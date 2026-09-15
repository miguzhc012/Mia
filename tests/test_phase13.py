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