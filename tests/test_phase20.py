"""Testes da Fase 12: Nós Distribuídos (NodeManager, Sync, Offline, Conflict)."""
import os
import tempfile

import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, EventType
from mia_pkg.distributed import (
    NodeManager, NodeRole, NodeStatus, SyncEngine, SyncSnapshot, SyncEvent,
    OfflineMode, ConflictResolver, Node,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestNodeManager:
    def test_local_node_online(self, db):
        nm = NodeManager(db, role=NodeRole.CLIENT, name="pc")
        local = nm.local()
        assert local.role == NodeRole.CLIENT
        assert local.status == NodeStatus.ONLINE

    def test_master_role(self, db):
        nm = NodeManager(db, role=NodeRole.MASTER, name="vps")
        assert nm.is_master()

    def test_register_peer_emits_event(self, db):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.NODE_ONLINE, lambda e: got.append(e))
        nm = NodeManager(db, bus=bus, role=NodeRole.MASTER)
        node = nm.register_peer("peer-1", "celular", NodeRole.CLIENT)
        assert node.id == "peer-1"
        assert len(got) == 1

    def test_mark_offline(self, db):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.NODE_OFFLINE, lambda e: got.append(e))
        nm = NodeManager(db, bus=bus)
        nm.register_peer("peer-1", "celular", NodeRole.CLIENT)
        nm.mark_offline("peer-1")
        assert nm.get("peer-1").status == NodeStatus.OFFLINE
        assert len(got) == 1

    def test_heartbeat_unknown_registers(self, db):
        nm = NodeManager(db)
        nm.heartbeat("novo-peer")
        assert nm.get("novo-peer") is not None

    def test_list_nodes(self, db):
        nm = NodeManager(db)
        nm.register_peer("a", "A", NodeRole.CLIENT)
        nm.register_peer("b", "B", NodeRole.CLIENT)
        assert len(nm.list_nodes()) == 3  # local + a + b


class TestSyncEngine:
    def test_create_snapshot_contains_tables(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        snap = sync.create_snapshot()
        assert "memory_objects" in snap.tables
        assert snap.checksum != ""  # calculado

    def test_snapshot_checksum_stable(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        s1 = sync.create_snapshot()
        s2 = sync.create_snapshot()
        assert s1.checksum == s2.checksum

    def test_snapshot_detects_change(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        s1 = sync.create_snapshot()
        # adiciona memória
        from mia_pkg.memory import MemoryStore, MemoryObject
        MemoryStore(db).create(MemoryObject(content="novo", importance=0.5))
        s2 = sync.create_snapshot()
        assert s1.checksum != s2.checksum

    def test_apply_snapshot_transfers_data(self, db):
        """master → client: dados do master aplicados no client."""
        # master com dados
        master_db = SQLiteConnection(":memory:")
        master_db.connect(); master_db.init_schema()
        from mia_pkg.memory import MemoryStore, MemoryObject
        MemoryStore(master_db).create(MemoryObject(content="dado do master", importance=0.8))
        master_nm = NodeManager(master_db, role=NodeRole.MASTER, name="vps")
        master_sync = SyncEngine(master_db, master_nm)
        snap = master_sync.create_snapshot()

        # client vazio aplica
        client_nm = NodeManager(db, role=NodeRole.CLIENT, name="pc")
        client_sync = SyncEngine(db, client_nm)
        applied = client_sync.apply_snapshot(snap)
        assert applied >= 1
        mems = MemoryStore(db).list_by_importance()
        assert len(mems) >= 1
        assert any(m.content == "dado do master" for m in mems)
        master_db.close()

    def test_apply_snapshot_sync_event_emitted(self, db):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.SYNC_COMPLETED, lambda e: got.append(e))
        nm = NodeManager(db)
        sync = SyncEngine(db, nm, bus=bus)
        sync.apply_snapshot(sync.create_snapshot())
        assert len(got) == 1


class TestSyncQueue:
    def test_enqueue_pending(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        ev = sync.enqueue("memory", {"content": "x"})
        assert ev.node_id == nm.local().id
        assert not ev.applied
        assert len(sync.pending_events()) == 1

    def test_flush_queue_marks_applied(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        sync.enqueue("memory", {"content": "x"})
        sent = sync.flush_queue(lambda e: True)
        assert sent == 1
        assert sync.pending_events() == []

    def test_flush_failure_keeps_event(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        sync.enqueue("memory", {"content": "x"})
        sent = sync.flush_queue(lambda e: (_ for _ in ()).throw(RuntimeError("offline")))
        assert sent == 0
        assert len(sync.pending_events()) == 1

    def test_serialize_load_roundtrip(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        sync.enqueue("memory", {"content": "x"})
        sync.enqueue("belief", {"content": "y"})
        raw = sync.serialize_queue()

        sync2 = SyncEngine(db, NodeManager(db))
        sync2.load_queue(raw)
        assert len(sync2.pending_events()) == 2


class TestOfflineMode:
    def test_reads_from_snapshot_offline(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        snap = sync.create_snapshot()

        offline = OfflineMode(db, sync)
        offline.save_snapshot(snap)
        assert offline.is_offline()
        rows = offline.read_state("memory_objects")
        assert isinstance(rows, list)

    def test_save_load_disk(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        snap = sync.create_snapshot()
        offline = OfflineMode(db, sync)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            offline.save_snapshot(snap, path)
            assert os.path.exists(path)

            offline2 = OfflineMode(db, SyncEngine(db, NodeManager(db)))
            loaded = offline2.load_snapshot_from_disk(path)
            assert loaded is not None
            assert loaded.checksum == snap.checksum

    def test_no_snapshot_initial(self, db):
        nm = NodeManager(db)
        sync = SyncEngine(db, nm)
        offline = OfflineMode(db, sync)
        assert not offline.has_snapshot()
        assert not offline.is_offline()


class TestConflictResolver:
    def test_master_wins_over_client(self, db):
        resolver = ConflictResolver(master_id="m")
        local = Node(id="client", role=NodeRole.CLIENT, status=NodeStatus.ONLINE, last_seen_s=100)
        incoming = Node(id="m", role=NodeRole.MASTER, status=NodeStatus.ONLINE, last_seen_s=50)
        winner = resolver.resolve(local, incoming)
        assert winner.role == NodeRole.MASTER

    def test_local_master_wins_over_client(self, db):
        resolver = ConflictResolver(master_id="m")
        local = Node(id="m", role=NodeRole.MASTER, status=NodeStatus.ONLINE, last_seen_s=50)
        incoming = Node(id="c", role=NodeRole.CLIENT, status=NodeStatus.ONLINE, last_seen_s=100)
        winner = resolver.resolve(local, incoming)
        assert winner.role == NodeRole.MASTER

    def test_client_newest_wins(self, db):
        resolver = ConflictResolver(master_id="m")
        local = Node(id="c1", role=NodeRole.CLIENT, status=NodeStatus.ONLINE, last_seen_s=100)
        incoming = Node(id="c2", role=NodeRole.CLIENT, status=NodeStatus.ONLINE, last_seen_s=200)
        winner = resolver.resolve(local, incoming)
        assert winner.id == "c2"

    def test_should_apply_master_snapshot(self, db):
        resolver = ConflictResolver(master_id="m")
        master = Node(role=NodeRole.MASTER)
        client = Node(role=NodeRole.CLIENT)
        # master snapshot aplica sempre
        assert resolver.should_apply(master, is_master_local=False)
        # client snapshot só aplica se não sou master
        assert resolver.should_apply(client, is_master_local=False)
        assert not resolver.should_apply(client, is_master_local=True)