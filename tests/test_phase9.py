"""Testes da Fase 2: Retrieval melhorado, Consolidação, Scheduler."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.memory import MemoryStore, MemoryObject, MemoryType
from mia_pkg.consolidation import (
    RetrievalEngine, MemoryAssociations, MemoryConsolidator, MemoryScheduler,
    tokenize,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# Tokenize
# ======================================================================

class TestTokenize:
    def test_basic(self):
        assert tokenize("Olá Miguel! Como vai?") == ["olá", "miguel", "como", "vai"]

    def test_accented(self):
        assert tokenize("Você está bem?") == ["você", "está", "bem"]


# ======================================================================
# Retrieval Engine
# ======================================================================

class TestRetrievalEngine:
    def _seed(self, db):
        store = MemoryStore(db)
        store.create(MemoryObject(
            content="Miguel gosta de café preto",
            type=MemoryType.preference.value, source="chat", importance=0.9,
        ))
        store.create(MemoryObject(
            content="Sabrina adora música clássica",
            type=MemoryType.preference.value, source="chat", importance=0.5,
        ))
        store.create(MemoryObject(
            content="O dia estava chuvoso",
            type=MemoryType.experience.value, source="chat", importance=0.2,
        ))

    def test_search_finds_relevant(self, db):
        self._seed(db)
        engine = RetrievalEngine(db)
        results = engine.search("café miguel", limit=5)
        assert len(results) >= 1
        assert "café" in results[0].content

    def test_ranking_importance_first(self, db):
        """Com match parecido, maior importância vem primeiro."""
        store = MemoryStore(db)
        store.create(MemoryObject(
            content="Tema importante para Miguel",
            type=MemoryType.fact.value, source="chat", importance=0.9,
        ))
        store.create(MemoryObject(
            content="Tema menos importante para Miguel",
            type=MemoryType.fact.value, source="chat", importance=0.1,
        ))
        engine = RetrievalEngine(db)
        results = engine.search("Miguel tema", limit=2)
        assert results[0].importance >= results[1].importance

    def test_empty_query_returns_by_importance(self, db):
        self._seed(db)
        engine = RetrievalEngine(db)
        results = engine.search("", limit=5)
        assert results[0].importance == 0.9

    def test_min_importance_filter(self, db):
        self._seed(db)
        engine = RetrievalEngine(db)
        results = engine.search("Miguel", limit=10, min_importance=0.5)
        assert all(r.importance >= 0.5 for r in results)


# ======================================================================
# Memory Associations
# ======================================================================

class TestMemoryAssociations:
    def test_associate_and_get(self, db):
        store = MemoryStore(db)
        m1 = store.create(MemoryObject(content="primeira", importance=0.5))
        m2 = store.create(MemoryObject(content="segunda", importance=0.5))
        assoc = MemoryAssociations(db)
        assoc.associate(m1.id, m2.id)

        related = assoc.get_associations(m1.id)
        assert m2.id in related

    def test_find_related_objects(self, db):
        store = MemoryStore(db)
        m1 = store.create(MemoryObject(content="café", importance=0.5))
        m2 = store.create(MemoryObject(content="cafeteira", importance=0.5))
        assoc = MemoryAssociations(db)
        assoc.associate(m1.id, m2.id)

        related = assoc.find_related(m1.id)
        assert len(related) == 1
        assert related[0].content == "cafeteira"

    def test_associate_idempotent(self, db):
        store = MemoryStore(db)
        m1 = store.create(MemoryObject(content="a", importance=0.5))
        m2 = store.create(MemoryObject(content="b", importance=0.5))
        assoc = MemoryAssociations(db)
        assoc.associate(m1.id, m2.id)
        assoc.associate(m1.id, m2.id)
        assert len(assoc.get_associations(m1.id)) == 1


# ======================================================================
# Memory Consolidation
# ======================================================================

class TestMemoryConsolidation:
    def test_consolidates_after_threshold(self, db):
        consolidator = MemoryConsolidator(db, turns_threshold=4)
        messages = [
            {"role": "user", "content": f"fala sobre python {i}"}
            for i in range(5)
        ]
        created = consolidator.consolidate_conversation(messages)
        assert len(created) >= 1
        assert created[0].is_consolidated is True
        assert created[0].type == MemoryType.experience.value

    def test_short_conversation_not_consolidated(self, db):
        consolidator = MemoryConsolidator(db, turns_threshold=4)
        messages = [
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "ola"},
        ]
        created = consolidator.consolidate_conversation(messages)
        assert created == []

    def test_consolidated_memories_persist(self, db):
        consolidator = MemoryConsolidator(db, turns_threshold=2)
        messages = [
            {"role": "user", "content": "gosto muito de viajar para a praia 1"},
            {"role": "user", "content": "gosto muito de viajar para a praia 2"},
        ]
        consolidator.consolidate_conversation(messages)
        store = MemoryStore(db)
        mems = store.list_by_importance()
        assert any(m.is_consolidated for m in mems)

    def test_extracts_topics(self, db):
        consolidator = MemoryConsolidator(db)
        topics = consolidator._extract_topics("gosto de jogar futebol jogar bola")
        assert "jogar" in topics


# ======================================================================
# Memory Scheduler
# ======================================================================

class TestMemoryScheduler:
    def test_cleanup_expired(self, db):
        """Memórias velhas de baixa importância são removidas."""
        import uuid as _uuid
        from datetime import datetime, timezone, timedelta
        store = MemoryStore(db)
        old = datetime.now(timezone.utc) - timedelta(days=200)
        mem = MemoryObject(
            content="coisa velha e irrelevante",
            type=MemoryType.experience.value,
            source="test",
            importance=0.1,
            created_at=old.isoformat(),
            updated_at=old.isoformat(),
        )
        store.create(mem)
        # memória recente importante NÃO deve ser removida
        store.create(MemoryObject(
            content="coisa nova importante",
            type=MemoryType.fact.value,
            source="test",
            importance=0.9,
        ))

        scheduler = MemoryScheduler(db)
        removed = scheduler.cleanup_expired(max_age_days=90, min_importance=0.3)
        assert removed == 1
        assert store.count() == 1

    def test_decay_access_reduces_importance(self, db):
        """Memória não acessada há tempo perde importância."""
        from datetime import datetime, timezone, timedelta
        store = MemoryStore(db)
        old = datetime.now(timezone.utc) - timedelta(days=30)
        mem = MemoryObject(
            content="esquecida",
            type=MemoryType.experience.value,
            source="test",
            importance=0.8,
            last_accessed_at=old.isoformat(),
        )
        store.create(mem)

        scheduler = MemoryScheduler(db)
        scheduler.decay_access(decay_rate=0.01)
        after = store.get(mem.id)
        assert after.importance < 0.8

    def test_daily_maintenance(self, db):
        scheduler = MemoryScheduler(db)
        result = scheduler.run_daily_maintenance()
        assert "cleanup" in result
        assert result["count_before"] == result["count_after"]  # nada a limpar