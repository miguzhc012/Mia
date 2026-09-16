"""Testes da Budget Authority (H5/H6) — autoridade global de orçamento."""
import pytest

from mia_pkg.budget import BudgetAuthority, BudgetConfig
from mia_pkg.db import SQLiteConnection


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestBudgetAuthority:
    def test_external_call_limit(self, db):
        """Chamadas externas respeitam o teto diário."""
        ba = BudgetAuthority(BudgetConfig(max_daily_external_calls=3), db)
        assert ba.check_external_call()
        assert ba.check_external_call()
        assert ba.check_external_call()
        assert not ba.check_external_call()  # 4ª bloqueada

    def test_autonomous_limit(self, db):
        ba = BudgetAuthority(BudgetConfig(max_daily_autonomous_actions=2), db)
        assert ba.check_autonomous_action()
        assert ba.check_autonomous_action()
        assert not ba.check_autonomous_action()

    def test_cost_limit(self, db):
        """Custo total não pode estourar o orçamento."""
        ba = BudgetAuthority(BudgetConfig(max_total_cost=10.0), db)
        assert ba.spend(6.0)
        assert ba.spend(4.0)   # 10 == max, ok
        assert not ba.spend(0.1)  # > max → bloqueado
        assert ba.state["total_cost"] == pytest.approx(10.0)

    def test_restart_preserves_global_limit(self, db):
        """Limite GLOBAL sobrevive ao restart (nova instância, mesmo db)."""
        ba1 = BudgetAuthority(BudgetConfig(max_total_cost=100.0), db)
        ba1.spend(42.0)
        # "restart": nova instância (novo processo simulado)
        ba2 = BudgetAuthority(BudgetConfig(max_total_cost=100.0), db)
        assert ba2.state["total_cost"] == pytest.approx(42.0)
        # orçamento restante correto
        assert ba2.spend(58.0)
        assert not ba2.spend(1.0)

    def test_daily_counter_resets_on_new_day(self, db, monkeypatch):
        """Contador diário zera quando o dia muda (data real)."""
        ba = BudgetAuthority(BudgetConfig(max_daily_external_calls=2), db)
        assert ba.check_external_call()
        assert ba.check_external_call()
        assert not ba.check_external_call()
        # simula virar o dia
        from mia_pkg import budget as budget_mod
        monkeypatch.setattr(
            budget_mod.BudgetAuthority,
            "_today",
            staticmethod(lambda: "2099-01-02"),
        )
        assert ba.check_external_call()  # novo dia → liberado

    def test_process_local_fallback_warns(self, capsys):
        """Sem db → aviso explícito de que limites são process-local."""
        ba = BudgetAuthority(BudgetConfig(), None)
        ba.spend(1.0)  # dispara o aviso na 1ª persistência
        out = capsys.readouterr().out
        assert "sem persistência" in out

    def test_runtime_soft_limit(self, db):
        ba = BudgetAuthority(BudgetConfig(max_runtime_hours=1.0), db)
        ba.record_runtime(3600.0)  # 1h
        assert ba.can_run()
        ba.record_runtime(1.0)     # 1h + 1s
        assert not ba.can_run()

    def test_subordinated_governor_registered(self, db):
        """Governors locais podem ser subordinados (inspeção)."""
        ba = BudgetAuthority(BudgetConfig(), db)
        ba.subordinated(object())
        assert len(ba._subordinates) == 1

    def test_state_exposes_limits(self, db):
        ba = BudgetAuthority(BudgetConfig(max_total_cost=7.5), db)
        s = ba.state
        assert s["total_cost_max"] == 7.5
        assert s["persisted"] is True
        assert "violations" in s