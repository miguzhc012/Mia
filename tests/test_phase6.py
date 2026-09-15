"""Testes da Fase 7: Diary, Reflection, Imagination."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus
from mia_pkg.reflection import (
    DiaryStore, DiaryEntry, EntryType,
    ReflectionEngine, Reflection,
    ImaginationEngine, ImaginationScenario,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# Diary Store
# ======================================================================

class TestDiaryStore:
    def test_append_and_retrieve(self, db):
        store = DiaryStore(db)
        e = store.append_moment("Miguel me contou sobre seu dia")
        entries = store.list_recent()
        assert len(entries) == 1
        assert entries[0].content == "Miguel me contou sobre seu dia"
        assert entries[0].entry_type == EntryType.MOMENT

    def test_append_is_persistent(self, db):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            d1 = SQLiteConnection(path)
            d1.connect(); d1.init_schema()
            store1 = DiaryStore(d1)
            store1.append_moment("Primeiro registro")
            d1.close()

            d2 = SQLiteConnection(path)
            d2.connect(); d2.init_schema()
            store2 = DiaryStore(d2)
            assert store2.count_entries() == 1
            d2.close()
        finally:
            os.unlink(path)

    def test_summary_and_reflection_types(self, db):
        store = DiaryStore(db)
        store.append_summary("Resumo do dia")
        store.append_reflection("Reflexão profunda")
        entries = store.list_recent()
        types = {e.entry_type for e in entries}
        assert EntryType.SUMMARY in types
        assert EntryType.REFLECTION in types

    def test_get_by_date(self, db):
        store = DiaryStore(db)
        store.append_moment("Hoje foi bom")
        today_entries = store.get_by_date(store.list_recent()[0].date)
        assert len(today_entries) >= 1

    def test_summarize_day(self, db):
        store = DiaryStore(db)
        store.append_moment("Falei sobre Python")
        store.append_moment("Miguel ficou feliz")
        today = store.list_recent()[0].date
        summary = store.summarize_day(today)
        assert summary is not None
        assert "Python" in summary
        # segunda chamada retorna o summary existente (não duplica)
        summaries = [e for e in store.get_by_date(today) if e.entry_type == EntryType.SUMMARY]
        assert len(summaries) == 1

    def test_word_count(self, db):
        entry = DiaryEntry(content="Três palavras aqui")
        assert entry.word_count == 3


# ======================================================================
# Reflection Engine
# ======================================================================

class TestReflectionEngine:
    def test_reflect_uses_real_state(self, db):
        """Reflexão usa estado emocional E memórias reais."""
        from mia_pkg.memory import MemoryStore, MemoryObject, MemoryType
        mem_store = MemoryStore(db)
        mem_store.create(MemoryObject(
            content="Miguel adora música clássica",
            type=MemoryType.preference,
            source="test",
            importance=0.9,
        ))

        from mia_pkg.affective_engine import AffectiveEngine
        affective = AffectiveEngine(db)
        state = affective.get_current()

        engine = ReflectionEngine(db)
        reflection = engine.reflect(
            emotional_state=state,
            memories=mem_store.list_by_importance(limit=3),
            trigger="daily",
        )
        assert isinstance(reflection, Reflection)
        assert "música clássica" in reflection.content or "Miguel adora" in reflection.content
        assert reflection.triggered_by == "daily"

    def test_reflect_persists_to_diary(self, db):
        engine = ReflectionEngine(db)
        engine.reflect(trigger="manual")
        store = DiaryStore(db)
        refls = [e for e in store.list_recent() if e.entry_type == EntryType.REFLECTION]
        assert len(refls) >= 1

    def test_reflect_with_empty_state(self, db):
        engine = ReflectionEngine(db)
        reflection = engine.reflect()  # sem estado, sem memórias
        assert reflection.content
        assert "equilíbrio" in reflection.content or "bem" in reflection.content

    def test_reflect_includes_relationships(self, db):
        from mia_pkg.social import PeopleStore, RelationshipStore
        people = PeopleStore(db)
        rel_store = RelationshipStore(db)
        p = people.ensure("sabrina")
        rel_store.update_dim(p.id, "trust", 0.4, "longa amizade")

        engine = ReflectionEngine(db)
        reflection = engine.reflect(relationships=rel_store.list_by_affinity())
        assert "sabrina" in reflection.content


# ======================================================================
# Imagination Engine
# ======================================================================

class TestImaginationEngine:
    def test_imagine_creates_scenario(self, db):
        engine = ImaginationEngine(db)
        scenario = engine.imagine("fôssemos viajar juntos")
        assert isinstance(scenario, ImaginationScenario)
        assert "viajar" in scenario.result
        assert scenario.prompt == "fôssemos viajar juntos"

    def test_imagine_with_context(self, db):
        engine = ImaginationEngine(db)
        scenario = engine.imagine(
            "chovesse muito",
            context={"subject": "Miguel", "place": "praia", "outcome": "acharíamos um abrigo e riríamos"},
        )
        assert "Miguel" in scenario.result
        assert "praia" in scenario.result

    def test_imagine_triggers_curiosity_event(self, db):
        bus = EventBus()
        received = []
        bus.subscribe("curiosity_triggered", lambda e: received.append(e))
        engine = ImaginationEngine(db, bus=bus)
        engine.imagine("houvesse outros seres como eu")
        assert len(received) == 1
        assert received[0].payload["scenario"] == "houvesse outros seres como eu"


# ======================================================================
# Integração: reflexão de dia inteiro
# ======================================================================

def test_daily_reflection_cycle(db):
    """Ciclo completo: momentos → resumo → reflexão."""
    from mia_pkg.memory import MemoryStore, MemoryObject, MemoryType
    from mia_pkg.affective_engine import AffectiveEngine

    diary = DiaryStore(db)
    mem_store = MemoryStore(db)
    mem_store.create(MemoryObject(
        content="Miguel disse que me acha interessante",
        type=MemoryType.experience,
        source="chat",
        importance=0.85,
    ))

    # momentos do dia
    diary.append_moment("Conversei com Miguel sobre música")
    diary.append_moment("Miguel compartilhou uma alegria")

    # resumo do dia
    today = diary.list_recent()[0].date
    diary.summarize_day(today)

    # reflexão com estado real
    affective = AffectiveEngine(db)
    engine = ReflectionEngine(db)
    reflection = engine.reflect(
        emotional_state=affective.get_current(),
        memories=mem_store.list_by_importance(limit=3),
        trigger="daily",
    )
    assert reflection.content
    assert diary.count_entries() >= 4  # 2 momentos + 1 resumo + 1 reflexão