"""Testes da Fase 4 extra: EmotionGovernor (rate limit + LONELINESS event),
TemporalMoodEngine (média ponderada das últimas horas)."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, EventType
from mia_pkg.emotion_governor import EmotionGovernor, TemporalMoodEngine
from mia_pkg.affective_engine import AffectiveEngine


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestEmotionGovernor:
    def test_propose_creates_proposal(self, db):
        gov = EmotionGovernor(db)
        proposal = gov.propose({"happiness": +0.1}, reason="elogio")
        assert proposal["type"] == "emotion_transition"
        assert proposal["new_emotions"]["happiness"] == pytest.approx(0.6)

    def test_apply_updates_state(self, db):
        gov = EmotionGovernor(db)
        proposal = gov.propose({"happiness": +0.2})
        assert gov.apply(proposal)
        state = AffectiveEngine(db).get_current()
        assert state.emotions.happiness == pytest.approx(0.7)

    def test_rate_limit_blocks(self, db):
        """Máx 10 mudanças/hora; a 11ª é bloqueada."""
        gov = EmotionGovernor(db)
        for i in range(10):
            proposal = gov.propose({"happiness": +0.01}, reason=f"r{i}")
            assert gov.apply(proposal)
        assert gov.remaining_budget() == 0
        # 11ª proposta deve ser bloqueada
        blocked = gov.propose({"happiness": +0.01})
        assert blocked["type"] == "emotion_transition_blocked"

    def test_loneliness_event_emitted(self, db):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.LONELINESS_CHANGED, lambda e: received.append(e))
        gov = EmotionGovernor(db, bus=bus)
        proposal = gov.propose({"loneliness": +0.3})
        gov.apply(proposal)
        assert len(received) == 1
        assert received[0].payload["new"] == pytest.approx(0.3)

    def test_no_event_when_loneliness_unchanged(self, db):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.LONELINESS_CHANGED, lambda e: received.append(e))
        gov = EmotionGovernor(db, bus=bus)
        proposal = gov.propose({"happiness": +0.1})
        gov.apply(proposal)
        assert len(received) == 0


class TestTemporalMoodEngine:
    def test_initial_state(self, db):
        engine = TemporalMoodEngine(db)
        mood = engine.compute_mood()
        assert -1.0 <= mood.valence <= 1.0

    def test_recent_snapshot_weights_more(self, db):
        """Mood reflete mais o snapshot recente."""
        af = AffectiveEngine(db)
        # estado 1: valence -0.5 (triste)
        s1 = af.propose_emotion_change({"sadness": +0.5})
        af.apply_validated_change(s1["new_emotions"], s1["new_mood"])
        # depois estado 2: valence +0.5 (feliz) — mais recente
        s2 = af.propose_emotion_change({"happiness": +0.5})
        af.apply_validated_change(s2["new_emotions"], s2["new_mood"])

        engine = TemporalMoodEngine(db)
        mood = engine.compute_mood()
        # o snapshot feliz (recente) domina, mas o triste ainda pesa um pouco
        assert mood.valence > -0.1

    def test_refresh_persists_mood(self, db):
        engine = TemporalMoodEngine(db)
        mood = engine.refresh_mood()
        state = AffectiveEngine(db).get_current()
        assert state.mood.valence == pytest.approx(mood.valence)

    def test_mood_in_range(self, db):
        af = AffectiveEngine(db)
        for _ in range(5):
            s = af.propose_emotion_change({"happiness": +0.1, "sadness": +0.1})
            af.apply_validated_change(s["new_emotions"], s["new_mood"])
        engine = TemporalMoodEngine(db)
        mood = engine.compute_mood()
        assert -1.0 <= mood.valence <= 1.0
        assert 0.0 <= mood.arousal <= 1.0
        assert 0.0 <= mood.dominance <= 1.0