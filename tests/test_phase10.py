"""Testes da Fase 7: Belief Revision com evidência."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.beliefs import BeliefStore, Belief, BeliefStatus
from mia_pkg.belief_revision import (
    BeliefRevisionEngine, Evidence, BeliefRevisionResult,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestBeliefRevision:
    def test_supporting_evidence_increases_confidence(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel gosta de café", confidence=0.6))
        engine = BeliefRevisionEngine(db)
        result = engine.process_evidence_for(b.id, Evidence(
            proposition="Miguel adora café",
            supports=True, weight=0.2, source="conversa",
        ))
        assert result.action == "increased"
        assert result.confidence_after == pytest.approx(0.8)

    def test_contradicting_evidence_decreases(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel gosta de café", confidence=0.6))
        engine = BeliefRevisionEngine(db)
        result = engine.process_evidence_for(b.id, Evidence(
            proposition="Miguel odeia café",
            supports=False, weight=0.2, source="conversa",
        ))
        assert result.action == "decreased"
        assert result.confidence_after == pytest.approx(0.4)

    def test_belief_rejected_below_threshold(self, db):
        """Confiança < 0.2 → crença rejeitada (esquecida)."""
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel gosta de café", confidence=0.3))
        engine = BeliefRevisionEngine(db)
        result = engine.process_evidence_for(b.id, Evidence(
            proposition="Miguel odeia café",
            supports=False, weight=0.2, source="forte evidência",
        ))
        assert result.action == "rejected"
        updated = store.get(b.id)
        assert updated.status == BeliefStatus.rejected

    def test_auto_revision_across_all_similar(self, db):
        """Evidência contraditória atinge TODAS as crenças ativas similares."""
        store = BeliefStore(db)
        b1 = store.create(Belief(proposition="Miguel gosta muito de café", confidence=0.6))
        b2 = store.create(Belief(proposition="Miguel bebe café diariamente", confidence=0.5))
        b3 = store.create(Belief(proposition="O céu é azul", confidence=0.9))  # não relacionada

        engine = BeliefRevisionEngine(db)
        results = engine.process_evidence(Evidence(
            proposition="Miguel parou de tomar café",
            supports=False, weight=0.2, source="conversa",
        ))
        affected_ids = {r.belief_id for r in results}
        assert b1.id in affected_ids
        assert b2.id in affected_ids
        assert b3.id not in affected_ids

    def test_revision_history_tracked(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel gosta de café", confidence=0.5))
        engine = BeliefRevisionEngine(db)
        engine.process_evidence_for(b.id, Evidence(
            proposition="Miguel odeia café", supports=False, weight=0.1,
        ))
        updated = store.get(b.id)
        assert len(updated.revision_history) >= 1
        assert updated.revision_history[0]["old_confidence"] == 0.5

    def test_confidence_clamped_at_zero(self, db):
        store = BeliefStore(db)
        b = store.create(Belief(proposition="Miguel gosta de café", confidence=0.1))
        engine = BeliefRevisionEngine(db)
        result = engine.process_evidence_for(b.id, Evidence(
            proposition="Miguel odeia café", supports=False, weight=0.5,
        ))
        assert result.confidence_after >= 0.0


class TestEvidenceSimilarity:
    def test_similar_returns_true(self, db):
        engine = BeliefRevisionEngine(db)
        assert engine._is_similar("Miguel gosta de café", "Miguel ama café")

    def test_different_returns_false(self, db):
        engine = BeliefRevisionEngine(db)
        assert not engine._is_similar("O céu é azul", "Miguel gosta de café")

    def test_short_words_no_match(self, db):
        engine = BeliefRevisionEngine(db)
        assert not engine._is_similar("é bom", "é ruim")  # palavras curtas demais