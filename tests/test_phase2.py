"""Testes para módulos novos: beliefs, needs_desires, attention_policy."""
from __future__ import annotations

import os
import tempfile
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.beliefs import Belief, BeliefStore, BeliefStatus
from mia_pkg.needs_desires import (
    Need, NeedType, Desire, DesireType, NeedsDesiresStore,
)
from mia_pkg.attention_policy import (
    AttentionEvaluation, AttentionPolicy, AttentionDecision,
)


@pytest.fixture
def db():
    """Banco temporário para testes."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = SQLiteConnection(path)
    conn.connect()
    conn.init_schema()
    yield conn
    conn.close()
    os.remove(path)
    for ext in ("-wal", "-shm"):
        try:
            os.remove(path + ext)
        except OSError:
            pass


# ======================================================================
# Beliefs
# ======================================================================

class TestBeliefs:
    def test_create_belief(self, db):
        store = BeliefStore(db)
        b = Belief(proposition="Miguel gosta de música", confidence=0.7)
        created = store.create(b)
        assert created.id == b.id
        assert created.confidence == 0.7
        assert created.status == BeliefStatus.active

    def test_increase_confidence(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel é gentil", confidence=0.5))
        updated = store.increase_confidence(b.id, 0.3, evidence="Observação hoje")
        assert updated.confidence == 0.8
        assert len(updated.revision_history) == 1

    def test_decrease_confidence(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel sempre responde rápido", confidence=0.6))
        updated = store.decrease_confidence(b.id, 0.4, evidence="Não respondeu por 2h")
        assert abs(updated.confidence - 0.2) < 1e-10

    def test_confidence_clamped(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Teste", confidence=0.9))
        updated = store.increase_confidence(b.id, 0.5)
        assert updated.confidence == 1.0  # clamped

    def test_revise_belief(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Mia é paciente", confidence=0.8))
        revised = store.revise(b.id, "Mia percebe que não é tão paciente", 0.5, reason="Experiência de ignorada")
        assert revised.proposition == "Mia percebe que não é tão paciente"
        assert revised.status == BeliefStatus.revised
        assert len(revised.revision_history) == 1

    def test_reject_belief(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel não gosta de música", confidence=0.3))
        rejected = store.reject(b.id, reason="Miguel ouviu música hoje")
        assert rejected.status == BeliefStatus.rejected

    def test_list_active(self, db):
        store = BeliefStore(db)
        store.create(Belief(proposition="A", confidence=0.5))
        store.create(Belief(proposition="B", confidence=0.5))
        store.create(Belief(proposition="C", confidence=0.5))
        active = store.list_active()
        assert len(active) == 3

    def test_belief_lifecycle(self, db):
        """Ciclo completo: criar → aumentar → reduzir → revisar."""
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel é calmo", confidence=0.5))
        store.increase_confidence(b.id, 0.2)
        store.decrease_confidence(b.id, 0.3, evidence="Brigou hoje")
        final = store.revise(b.id, "Miguel pode ser intenso às vezes", 0.4)
        assert final.status == BeliefStatus.revised
        assert len(final.revision_history) == 3


# ======================================================================
# Needs & Desires
# ======================================================================

class TestNeedsDesires:
    def test_create_need(self, db):
        store = NeedsDesiresStore(db)
        n = Need(need_type=NeedType.social_interaction, intensity=0.8)
        created = store.create_need(n)
        assert created.need_type == NeedType.social_interaction
        assert created.intensity == 0.8

    def test_fulfill_need(self, db):
        store = NeedsDesiresStore(db)
        n = store.create_need(Need(need_type=NeedType.attention, intensity=0.6))
        fulfilled = store.fulfill_need(n.id)
        assert fulfilled.satisfied is True
        assert fulfilled.last_fulfilled_at is not None

    def test_list_unfulfilled_needs(self, db):
        store = NeedsDesiresStore(db)
        store.create_need(Need(need_type=NeedType.rest, intensity=0.3))
        store.create_need(Need(need_type=NeedType.novelty, intensity=0.9))
        unfulfilled = store.list_unfulfilled_needs()
        assert len(unfulfilled) == 2
        assert unfulfilled[0].intensity >= unfulfilled[1].intensity

    def test_create_desire(self, db):
        store = NeedsDesiresStore(db)
        d = Desire(description="Quero conversar sobre música", desire_type=DesireType.interaction)
        created = store.create_desire(d)
        assert created.description == "Quero conversar sobre música"

    def test_fulfill_desire(self, db):
        store = NeedsDesiresStore(db)
        d = store.create_desire(Desire(description="Investigar isso", desire_type=DesireType.exploration))
        fulfilled = store.fulfill_desire(d.id)
        assert fulfilled.fulfilled is True

    def test_need_vs_desire_distinction(self, db):
        """NEED ≠ DESIRE (§16)."""
        store = NeedsDesiresStore(db)
        store.create_need(Need(need_type=NeedType.social_interaction, intensity=0.7))
        store.create_desire(Desire(description="Quero conversar", desire_type=DesireType.interaction, priority=0.8))
        needs = store.list_unfulfilled_needs()
        desires = store.list_unfulfilled_desires()
        # São tabelas diferentes, mas ambos existem
        assert len(needs) == 1
        assert len(desires) == 1
        assert desires[0].priority == 0.8


# ======================================================================
# Attention Policy
# ======================================================================

class TestAttentionPolicy:
    def test_low_relevance_ignore(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(event_type="noise", relevance=0.1)
        decision = policy.evaluate(ev)
        assert decision == AttentionDecision.IGNORE

    def test_high_urgency_act(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(
            event_type="danger", relevance=0.9, urgency=0.95
        )
        decision = policy.evaluate(ev)
        assert decision == AttentionDecision.ACT

    def test_user_unavailable_wait(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(
            event_type="question", relevance=0.6, urgency=0.5, user_available=False
        )
        decision = policy.evaluate(ev)
        assert decision == AttentionDecision.WAIT

    def test_high_importance_favorable_state_act(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(
            event_type="important_update",
            relevance=0.7,
            importance=0.9,
            internal_state={"mood_valence": 0.3, "overloaded": False},
        )
        decision = policy.evaluate(ev)
        assert decision == AttentionDecision.ACT

    def test_overloaded_state_wait(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(
            event_type="info",
            relevance=0.7,
            importance=0.8,
            internal_state={"overloaded": True},
        )
        decision = policy.evaluate(ev)
        assert decision == AttentionDecision.WAIT

    def test_decision_logged(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(event_type="test", relevance=0.5)
        policy.evaluate(ev)
        recent = policy.recent_decisions()
        assert len(recent) == 1
        assert recent[0]["event_type"] == "test"

    def test_extreme_negative_state_blocks_action(self, db):
        policy = AttentionPolicy(db)
        ev = AttentionEvaluation(
            event_type="opportunity",
            relevance=0.8,
            importance=0.9,
            internal_state={"mood_valence": -0.9, "overloaded": False},
        )
        decision = policy.evaluate(ev)
        assert decision == AttentionDecision.WAIT
