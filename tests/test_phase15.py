"""Testes da Fase 14: World Awareness (Research, Interests, Relevance, Knowledge)."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, EventType
from mia_pkg.world import (
    InterestTracker, RelevanceScorer, KnowledgeStore,
    WorldResearchAgent, IdleResearcher,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# Interest Tracker
# ======================================================================

class TestInterestTracker:
    def test_observe_text_detects_frequent_words(self, db):
        tracker = InterestTracker(db)
        tracker.observe_text(
            "gosto de jogar futebol e treinar futebol e assistir futebol",
        )
        interest = tracker.get("futebol")
        assert interest is not None
        assert interest.weight > 0.3

    def test_short_words_ignored(self, db):
        tracker = InterestTracker(db)
        tracker.observe_text("eu a o e de um")
        assert tracker.get_top(10) == []

    def test_stopwords_excluded(self, db):
        tracker = InterestTracker(db)
        tracker.observe_text("quero muito muito muito isso isso isso")
        assert tracker.get("quero") is None

    def test_seed_from_personality(self, db):
        tracker = InterestTracker(db)
        # personalidade default tem curiosity=0.5 — não seeda muito
        tracker.seed_from_personality()
        # mas pode ter interesses vazios
        assert isinstance(tracker.get_top(3), list)

    def test_decay_removes_stale(self, db):
        import time as _time
        tracker = InterestTracker(db)
        tracker._bump("antigo", delta=0.5, source="test")
        tracker._interests["antigo"].last_seen = _time.time() - 30 * 86400
        tracker.decay()
        assert tracker.get("antigo") is None

    def test_personality_seeds_when_high(self, db):
        from mia_pkg.identity import IdentityManager, PersonalityState, PersonalityVector
        tracker = InterestTracker(db)
        # aumenta curiosity da personalidade
        im = IdentityManager(db)
        traits = PersonalityVector(curiosity=0.9, openness=0.9)
        im.apply_validated_personality(traits.to_dict(), 2)
        tracker.seed_from_personality()
        assert tracker.get("aprendizado") is not None


# ======================================================================
# Relevance Scorer
# ======================================================================

class TestRelevanceScorer:
    def test_relevant_topics_scored_high(self, db):
        tracker = InterestTracker(db)
        tracker._bump("inteligencia", delta=0.5, source="test")
        scorer = RelevanceScorer(db, tracker)
        score = scorer.score("inteligencia artificial avanca em novas areas")
        assert score > 0.3

    def test_irrelevant_text_low(self, db):
        tracker = InterestTracker(db)
        scorer = RelevanceScorer(db, tracker)
        score = scorer.score("abc xyz qwerty")  # sem match, curto
        assert score < 0.45

    def test_empty_text_zero(self, db):
        tracker = InterestTracker(db)
        scorer = RelevanceScorer(db, tracker)
        assert scorer.score("") == 0.0

    def test_threshold_filter(self, db):
        tracker = InterestTracker(db)
        scorer = RelevanceScorer(db, tracker)
        assert not scorer.is_relevant("abc xyz qwerty")


# ======================================================================
# Knowledge Store
# ======================================================================

class TestKnowledgeStore:
    def test_store_and_retrieve(self, db):
        ks = KnowledgeStore(db)
        mem = ks.store("ia", "descoberta importante sobre IA", importance=0.8)
        assert mem is not None
        results = ks.get_topic("ia")
        assert len(results) >= 1
        assert "knowledge:ia" in results[0].content

    def test_store_creates_person(self, db):
        """FK person_id='mundo' exige pessoa criada."""
        ks = KnowledgeStore(db)
        mem = ks.store("teste", "conteudo", importance=0.5)
        assert mem is not None


# ======================================================================
# World Research Agent
# ======================================================================

class TestWorldResearch:
    def test_research_stores_relevant(self, db):
        tracker = InterestTracker(db)
        tracker._bump("cafe", delta=0.5, source="test")

        def fake_search(topic):
            return "cafe torrado artesanal ganha popularidade no mercado"

        agent = WorldResearchAgent(db, search_fn=fake_search, tracker=tracker)
        result = agent.research("cafe")
        assert result["success"]
        assert result["stored"] is True
        assert result["memory_id"] is not None

    def test_irrelevant_not_stored(self, db):
        def fake_search(topic):
            return "x y z w"

        agent = WorldResearchAgent(db, search_fn=fake_search)
        result = agent.research("nada")
        assert result["success"]
        assert result["stored"] is False
        assert result["memory_id"] is None

    def test_research_event_emitted(self, db):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.RESEARCH_COMPLETED, lambda e: received.append(e))

        def fake_search(topic):
            return "resultado qualquer sobre qualquer coisa"

        agent = WorldResearchAgent(db, search_fn=fake_search, bus=bus)
        agent.research("topico")
        assert len(received) == 1
        assert received[0].payload["topic"] == "topico"

    def test_rate_limiting(self, db):
        def fake_search(topic):
            return "conteudo de teste"

        agent = WorldResearchAgent(db, search_fn=fake_search)
        for _ in range(5):
            agent.research("topico")
        # 6ª tentativa imediata: bloqueada
        result = agent.research("topico")
        assert not result["success"]
        assert result["reason"] == "rate limit"


# ======================================================================
# Idle Researcher
# ======================================================================

class TestIdleResearcher:
    def test_researches_top_interests(self, db):
        tracker = InterestTracker(db)
        tracker._bump("musica", delta=0.6, source="test")
        tracker._bump("fraco", delta=0.1, source="test")

        def fake_search(topic):
            return f"noticia sobre {topic} atualizada"

        agent = WorldResearchAgent(db, search_fn=fake_search, tracker=tracker)
        idle = IdleResearcher(db, agent, min_interest_weight=0.5)
        results = idle.run_idle_round(max_topics=5)
        # apenas "musica" tem peso >= 0.5
        assert len(results) >= 1
        assert all(r["topic"] == "musica" for r in results)