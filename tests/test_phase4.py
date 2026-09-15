"""Testes da Fase 5: People, Relationship, Social Evaluator, Boundary Manager."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.social import (
    PeopleStore, RelationshipStore, SocialEvaluator, BoundaryManager,
    InteractionClass, BoundaryResponse,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# People Store
# ======================================================================

class TestPeopleStore:
    def test_ensure_creates(self, db):
        store = PeopleStore(db)
        p = store.ensure("Miguel")
        assert p.name == "miguel"
        assert p.first_seen is not None
        assert store.get(p.id) is not None

    def test_ensure_idempotent(self, db):
        store = PeopleStore(db)
        p1 = store.ensure("Miguel")
        p2 = store.ensure("Miguel")
        assert p1.id == p2.id

    def test_touch_updates_last_seen(self, db):
        store = PeopleStore(db)
        p = store.ensure("Miguel")
        store.touch(p.id)
        updated = store.get(p.id)
        assert updated.last_seen is not None

    def test_list(self, db):
        store = PeopleStore(db)
        store.ensure("Miguel")
        store.ensure("sabrina")
        assert len(store.list()) == 2


# ======================================================================
# Relationship Store
# ======================================================================

class TestRelationshipStore:
    def test_ensure_creates(self, db):
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("Miguel")
        rel = rel_store.ensure(p.id)
        assert rel.trust == 0.5
        assert rel.intimacy == 0.0
        assert rel.familiarity == 0.0

    def test_update_dim(self, db):
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("Miguel")
        rel_store.ensure(p.id)

        rel = rel_store.update_dim(p.id, "trust", 0.2, "bom")
        assert rel.trust == pytest.approx(0.7)

        rel = rel_store.update_dim(p.id, "trust", 0.5, "muito bom")
        assert rel.trust <= 1.0  # clamp

    def test_update_dim_clamps_low(self, db):
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("Miguel")
        rel_store.ensure(p.id)
        rel = rel_store.update_dim(p.id, "affinity", -0.9, "ruim")
        assert rel.affinity >= 0.0

    def test_invalid_dim_raises(self, db):
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("Miguel")
        with pytest.raises(ValueError):
            rel_store.update_dim(p.id, "not_a_dim", 0.1)

    def test_interaction_count_increments(self, db):
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("Miguel")
        rel_store.update_dim(p.id, "trust", 0.1)
        rel = rel_store.update_dim(p.id, "affinity", 0.1)
        assert rel.interaction_count >= 2

    def test_history_tracks(self, db):
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("Miguel")
        rel_store.update_dim(p.id, "trust", 0.1, "primeiro")
        rel = rel_store.get(p.id)
        assert len(rel.history) == 1
        assert rel.history[0]["dim"] == "trust"
        assert rel.history[0]["reason"] == "primeiro"


# ======================================================================
# Social Evaluator
# ======================================================================

class TestSocialEvaluator:
    def test_positive(self):
        ev = SocialEvaluator()
        result = ev.evaluate("obrigado pela ajuda, você é incrível!")
        assert result.interaction_class == InteractionClass.POSITIVE

    def test_negative(self):
        ev = SocialEvaluator()
        result = ev.evaluate("que dia horrível, detesto isso")
        assert result.interaction_class == InteractionClass.NEGATIVE

    def test_neutral(self):
        ev = SocialEvaluator()
        result = ev.evaluate("vou ao mercado comprar pão")
        assert result.interaction_class == InteractionClass.NEUTRAL

    def test_offensive_refuse(self):
        ev = SocialEvaluator()
        result = ev.evaluate("cala a boca, idiota!")
        assert result.interaction_class == InteractionClass.NEGATIVE
        assert result.boundary == BoundaryResponse.REFUSE


# ======================================================================
# Boundary Manager
# ======================================================================

class TestBoundaryManager:
    def test_positive_updates_relationship(self, db):
        bm = BoundaryManager(db)
        result = bm.process("obrigado, você é incrível", "Miguel")
        rel_store = RelationshipStore(db)
        people = PeopleStore(db)
        p = people.get_by_name("miguel")
        rel = rel_store.get(p.id)
        assert result.interaction_class == InteractionClass.POSITIVE
        assert rel.trust > 0.5
        assert rel.affinity > 0.5

    def test_offensive_decreases_trust(self, db):
        bm = BoundaryManager(db)
        result = bm.process("cala a boca, idiota!", "Miguel")
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.get_by_name("miguel")
        rel = rel_store.get(p.id)
        assert result.boundary == BoundaryResponse.REFUSE
        assert rel.trust < 0.5
        assert rel.affinity < 0.5

    def test_person_created(self, db):
        bm = BoundaryManager(db)
        bm.process("oi!", "sabrina")
        people = PeopleStore(db)
        assert people.get_by_name("sabrina") is not None


# ======================================================================
# Integração com ChatSession
# ======================================================================

def test_chat_session_creates_person_and_memory(db):
    """ChatSession cria pessoa antes da memória (FK ok)."""
    from mia_pkg.chat import ChatSession
    from mia_pkg.llm import LLMProviderChain
    from tests.test_phase3 import MockProvider

    chain = LLMProviderChain([MockProvider("Que legal!")])
    session = ChatSession(db, chain)
    turn = session.send("Gosto de programar em Python")
    assert turn.response_text == "Que legal!"

    # Pessoa criada
    p = session.people.get_by_name("miguel")
    assert p is not None

    # Memória criada com person_id válido
    mems = session.memory.list_by_importance(limit=5)
    assert len(mems) >= 1
    assert mems[0].person_id == p.id


def test_chat_session_social_evaluation(db):
    """Complimento positivo melhora relação."""
    from mia_pkg.chat import ChatSession
    from mia_pkg.llm import LLMProviderChain
    from tests.test_phase3 import MockProvider

    chain = LLMProviderChain([MockProvider("Obrigada!")])
    session = ChatSession(db, chain)
    session.send("você é incrível, obrigado!")

    p = session.people.get_by_name("miguel")
    rel = session.relationships.get(p.id)
    assert rel.trust > 0.5