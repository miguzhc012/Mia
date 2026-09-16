"""Restart tests (H24) — o sistema não pode funcionar só com o processo vivo.

Cada teste cria um banco, escreve estado, "reinicia" (nova instância sobre o
mesmo banco) e verifica que o estado persiste e é coerente.
"""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.identity_authority import IdentityAuthority
from mia_pkg.memory import MemoryObject, MemoryStore
from mia_pkg.identity import IdentityManager


def _new_db(path):
    db = SQLiteConnection(path)
    db.connect()
    db.init_schema()
    return db


class TestRestartPersistence:
    def test_memory_survives_restart(self, tmp_path):
        db1 = _new_db(tmp_path / "m.db")
        s1 = MemoryStore(db1)
        obj = s1.create(MemoryObject(content="antes do restart", source="test"))

        db2 = _new_db(tmp_path / "m.db")
        s2 = MemoryStore(db2)
        got = s2.get(obj.id)
        assert got is not None
        assert got.content == "antes do restart"
        assert got.version == 1

    def test_identity_persists_restart(self, tmp_path):
        db1 = _new_db(tmp_path / "i.db")
        ia1 = IdentityAuthority(db1)
        ia1.process_interaction("elogio_recebido")
        traits_before = IdentityManager(db1).get_personality().traits

        db2 = _new_db(tmp_path / "i.db")
        ia2 = IdentityAuthority(db2)
        ia2.process_interaction("elogio_recebido")
        traits_after = IdentityManager(db2).get_personality().traits
        # agreeableness aumentou e não regrediu no restart
        assert traits_after.to_dict()["agreeableness"] >= traits_before.to_dict()["agreeableness"]

    def test_budget_persists_restart(self, tmp_path):
        from mia_pkg.budget import BudgetAuthority
        db1 = _new_db(tmp_path / "b.db")
        b1 = BudgetAuthority(db=db1)
        b1.spend(12.5)
        db2 = _new_db(tmp_path / "b.db")
        b2 = BudgetAuthority(db=db2)
        assert b2.state["total_cost"] >= 12.5  # não zerou no restart

    def test_personality_first_change_after_restart(self, tmp_path):
        """restart + primeira mudança (H2 regression) + persistência."""
        db1 = _new_db(tmp_path / "p.db")
        ia1 = IdentityAuthority(db1)
        changes = ia1.process_interaction("novidade_encontrada")
        assert len(changes) == 2  # openness + curiosity mudaram

        db2 = _new_db(tmp_path / "p.db")
        ia2 = IdentityAuthority(db2)
        # novo processo: primeira mudança NÃO deve ser bloqueada por rate limit
        changes2 = ia2.process_interaction("novidade_encontrada")
        assert len(changes2) >= 1