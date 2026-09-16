"""Testes de Memory Object versionado/imutável (H13)."""
import json

import pytest

from mia_pkg.memory import MemoryObject, MemoryStore
from mia_pkg.db import SQLiteConnection


@pytest.fixture
def store(tmp_path):
    db = SQLiteConnection(tmp_path / "mem.db")
    db.connect()
    db.init_schema()
    return MemoryStore(db)


def _obj(content="v1", importance=0.5):
    return MemoryObject(content=content, source="test", importance=importance)


class TestVersionedMemory:
    def test_add_creates_v1(self, store):
        obj = store.create(_obj("primeira"))
        assert obj.version == 1
        assert store.get(obj.id).content == "primeira"

    def test_update_creates_new_version_keeps_old(self, store):
        v1 = store.create(_obj("original"))
        v1.content = "modificada"
        v2 = store.update(v1)
        assert v2.id == v1.id
        assert v2.version == 2
        # versão atual é a nova
        current = store.get(v1.id)
        assert current.version == 2
        assert current.content == "modificada"
        # v1 continua recuperável
        old = store.get_version(v1.id, 1)
        assert old is not None
        assert old.content == "original"
        assert old.version == 1

    def test_revision_history_records_changes(self, store):
        v1 = store.create(_obj("conteudo-a"))
        v1.content = "conteudo-b"
        v2 = store.update(v1)
        hist = json.loads(v2.revision_history)
        assert len(hist) >= 1
        assert hist[-1]["version"] == 1
        assert hist[-1]["content"] == "conteudo-a"

    def test_update_no_double_history(self, store):
        v1 = store.create(_obj("a"))
        v1.content = "b"
        v2 = store.update(v1)
        v2.content = "c"
        v3 = store.update(v2)
        hist = json.loads(v3.revision_history)
        versions = [h["version"] for h in hist]
        assert versions == [1, 2]

    def test_update_importance_creates_version(self, store):
        v1 = store.create(_obj("x", importance=0.3))
        ok = store.update_importance(v1.id, 0.9)
        assert ok
        cur = store.get(v1.id)
        assert cur.version == 2
        assert cur.importance == 0.9
        old = store.get_version(v1.id, 1)
        assert old.importance == 0.3

    def test_update_importance_invalid_rejected(self, store):
        v1 = store.create(_obj("x"))
        assert store.update_importance(v1.id, 1.5) is False
        assert store.update_importance(v1.id, -0.1) is False
        assert store.get(v1.id).version == 1  # nada criado

    def test_list_versions_ordered(self, store):
        v1 = store.create(_obj("a"))
        v1.content = "b"
        store.update(v1)
        v2 = store.get(v1.id)
        v2.content = "c"
        store.update(v2)
        versions = store.list_versions(v1.id)
        assert [v["version"] for v in versions] == [3, 2, 1]

    def test_created_at_preserved_across_versions(self, store):
        v1 = store.create(_obj("a"))
        v1.content = "b"
        v2 = store.update(v1)
        assert v2.created_at == v1.created_at

    def test_get_version_missing_returns_none(self, store):
        v1 = store.create(_obj("a"))
        assert store.get_version(v1.id, 99) is None

    def test_multiple_objects_independent_versions(self, store):
        a = store.create(_obj("a1"))
        b = store.create(_obj("b1"))
        a.content = "a2"
        store.update(a)
        assert store.get(a.id).version == 2
        assert store.get(b.id).version == 1  # B não foi afetado