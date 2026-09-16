"""Testes da Fase 3: Identity Authority, evolução de personalidade."""
import time
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.identity import IdentityManager, PersonalityVector, PersonalityState
from mia_pkg.identity_authority import (
    IdentityAuthority, PersonalityChange, TRAIT_EFFECTS, TRAIT_RANGES,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
def authority(db):
    return IdentityAuthority(db)


class TestPersonalityEvolution:
    def test_novidade_increases_openness(self, db, authority):
        authority.reset_limits()  # remove rate limit inicial
        changes = authority.process_interaction("novidade_encontrada")
        assert any(c.trait == "openness" for c in changes)
        personality = IdentityManager(db).get_personality()
        assert personality.traits.openness > 0.5  # default era 0.5

    def test_traits_clamped_to_ranges(self, db, authority):
        """Muitas mudanças não ultrapassam o range (R3.1 mitigação)."""
        authority.reset_limits()
        authority.MIN_INTERVAL_SECONDS = 0.0
        for _ in range(50):
            authority.process_interaction("novidade_encontrada")
        personality = IdentityManager(db).get_personality()
        lo, hi = TRAIT_RANGES["openness"]
        assert lo <= personality.traits.openness <= hi

    def test_unknown_event_ignored(self, db, authority):
        changes = authority.process_interaction("evento_inexistente")
        assert changes == []

    def test_rate_limit_blocks_fast_changes(self, db, authority):
        """Duas mudanças no mesmo traço em sequência rápida são limitadas."""
        authority.reset_limits()
        first = authority.process_interaction("novidade_encontrada")
        second = authority.process_interaction("novidade_encontrada")
        # segunda chamada imediata: rate limit impede nova mudança
        assert len(second) == 0

    def test_text_interaction_curiosity(self, db, authority):
        authority.reset_limits()
        changes = authority.process_text_interaction("por que o céu é azul? e como funciona a luz?")
        assert any(c.trait == "curiosity" for c in changes)

    def test_text_interaction_praise(self, db, authority):
        authority.reset_limits()
        changes = authority.process_text_interaction("obrigado por tudo!")
        assert any(c.trait == "agreeableness" for c in changes)

    def test_text_interaction_stress(self, db, authority):
        authority.reset_limits()
        changes = authority.process_text_interaction("estou muito ansioso hoje")
        assert any(c.trait == "neuroticism" for c in changes)

    def test_personality_persists_across_instances(self, db, authority):
        authority.reset_limits()
        authority.process_interaction("novidade_encontrada")
        # nova instância lê o mesmo DB
        authority2 = IdentityAuthority(db)
        personality = authority2._identity.get_personality()
        assert personality.traits.openness > 0.5

    def test_version_increments(self, db, authority):
        authority.reset_limits()
        v0 = IdentityManager(db).get_personality().version
        authority.process_interaction("novidade_encontrada")
        v1 = IdentityManager(db).get_personality().version
        assert v1 == v0 + 1

    def test_history_tracked(self, db, authority):
        authority.reset_limits()
        changes = authority.process_interaction("novidade_encontrada")
        assert authority.history()  # não vazio


class TestTraitEffects:
    def test_all_events_have_valid_traits(self):
        """Todos os eventos mapeiam traços existentes do PersonalityVector."""
        valid = set(PersonalityVector().__dataclass_fields__.keys())
        for event, effects in TRAIT_EFFECTS.items():
            for trait in effects:
                assert trait in valid, f"{event} -> {trait} inválido"

    def test_all_trait_ranges_valid(self):
        for trait, (lo, hi) in TRAIT_RANGES.items():
            assert 0.0 <= lo < hi <= 1.0


# ----------------------------------------------------------------------
# Regressão H2: primeira mudança NÃO pode ser bloqueada em processo novo.
#
# O bug: `_last_change.get(trait, 0.0)` tratava traço nunca-mudado como
# "mudou no tempo 0" e `time.monotonic()` não começa em 0 → a primeira
# mudança legítima era silenciosamente bloqueada durante os primeiros
# MIN_INTERVAL_SECONDS (30s) do processo.
#
# Teste determinístico: controla o relógio via monkeypatch.
# ----------------------------------------------------------------------

class TestFirstChangeNotBlockedOnFreshProcess:
    def test_first_change_immediately_allowed(self, db, authority, monkeypatch):
        """Processo recém-iniciado: 1ª interação → mudança acontece."""
        clock = {"t": 0.5}  # monotonic de processo recém-iniciado
        monkeypatch.setattr(
            "mia_pkg.identity_authority.time.monotonic", lambda: clock["t"]
        )
        changes = authority.process_interaction("novidade_encontrada")
        assert changes, "primeira mudança legítima foi bloqueada"
        assert any(c.trait == "openness" for c in changes)

    def test_second_change_within_window_blocked(self, db, authority, monkeypatch):
        """Após a 1ª mudança, 2ª dentro de 30s é limitada (comportamento correto)."""
        clock = {"t": 0.5}
        monkeypatch.setattr(
            "mia_pkg.identity_authority.time.monotonic", lambda: clock["t"]
        )
        first = authority.process_interaction("novidade_encontrada")
        assert first
        second = authority.process_interaction("novidade_encontrada")
        assert second == [], "2ª mudança dentro da janela deveria ser limitada"

    def test_after_window_second_change_allowed(self, db, authority, monkeypatch):
        """Após 30s+, nova mudança no mesmo traço é permitida."""
        clock = {"t": 0.5}
        monkeypatch.setattr(
            "mia_pkg.identity_authority.time.monotonic", lambda: clock["t"]
        )
        first = authority.process_interaction("novidade_encontrada")
        assert first
        clock["t"] += 31.0  # passa da janela
        second = authority.process_interaction("novidade_encontrada")
        assert second, "mudança após a janela deveria ser permitida"

    def test_multiple_traits_independent_limits(self, db, authority, monkeypatch):
        """Traços diferentes têm limites independentes."""
        clock = {"t": 0.5}
        monkeypatch.setattr(
            "mia_pkg.identity_authority.time.monotonic", lambda: clock["t"]
        )
        c1 = authority.process_interaction("novidade_encontrada")  # openness, curiosity
        assert c1
        # mesmos traços de novo → bloqueado
        c2 = authority.process_interaction("novidade_encontrada")
        assert c2 == []
        # traço diferente (elogio → agreeableness) → permitido
        clock["t"] += 0.1
        c3 = authority.process_interaction("elogio_recebido")
        assert c3, "traço independente não deveria ser bloqueado"

    def test_reset_allows_immediate_change(self, db, authority, monkeypatch):
        """reset_limits zera o rate limit — próxima mudança imediata."""
        clock = {"t": 0.5}
        monkeypatch.setattr(
            "mia_pkg.identity_authority.time.monotonic", lambda: clock["t"]
        )
        authority.process_interaction("novidade_encontrada")
        authority.reset_limits()
        changes = authority.process_interaction("novidade_encontrada")
        assert changes

    def test_fresh_authority_after_persisted_change(self, db, authority, monkeypatch):
        """Restart de processo (nova instância) com histórico já persistido:
        o rate limit é por-instância (process-local), a primeira mudança
        da nova instância é permitida."""
        clock = {"t": 0.5}
        monkeypatch.setattr(
            "mia_pkg.identity_authority.time.monotonic", lambda: clock["t"]
        )
        authority.process_interaction("novidade_encontrada")
        # nova instância = novo processo (mesmo DB)
        authority2 = IdentityAuthority(db)
        changes = authority2.process_interaction("novidade_encontrada")
        assert changes, "nova instância não deveria herdar rate limit de processo antigo"