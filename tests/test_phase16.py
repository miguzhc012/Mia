"""Testes da Fase 16: Health Monitor, Backup/Restore."""
import os
import tempfile
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.monitoring import HealthMonitor, BackupManager
from mia_pkg.memory import MemoryStore, MemoryObject


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestHealthMonitor:
    def test_health_check_db_ok(self, db):
        monitor = HealthMonitor(db)
        report = monitor.health_check()
        assert report.db_ok is True

    def test_tables_counted(self, db):
        monitor = HealthMonitor(db)
        report = monitor.health_check()
        assert "memory_objects" in report.tables
        assert "identity_state" in report.tables

    def test_counts_reflect_data(self, db):
        store = MemoryStore(db)
        store.create(MemoryObject(content="teste 1", importance=0.5))
        store.create(MemoryObject(content="teste 2", importance=0.5))
        monitor = HealthMonitor(db)
        report = monitor.health_check()
        assert report.tables["memory_objects"] >= 2

    def test_component_status_all_ok(self, db):
        monitor = HealthMonitor(db)
        status = monitor.component_status()
        assert len(status) >= 20
        assert all(v == "ok" for v in status.values()), status

    def test_measure_latency(self, db):
        monitor = HealthMonitor(db)
        import time
        latency = monitor.measure_latency(time.sleep, 0.01, label="sleep")
        assert latency >= 8.0  # ~10ms


class TestBackupManager:
    def test_backup_and_restore(self, db):
        store = MemoryStore(db)
        store.create(MemoryObject(content="dado importante", importance=0.9))

        # backup para arquivo
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "backup.db")
            bm = BackupManager(db)
            assert bm.backup_to(path)
            assert os.path.exists(path)

            # novo DB, restaura
            db2 = SQLiteConnection(":memory:")
            db2.connect()
            db2.init_schema()
            bm2 = BackupManager(db2)
            assert bm2.restore_from(path)
            store2 = MemoryStore(db2)
            memories = store2.list_by_importance()
            assert any(m.content == "dado importante" for m in memories)
            db2.close()

    def test_backup_fails_with_bad_path(self, db):
        bm = BackupManager(db)
        assert not bm.backup_to("/caminho/inexistente/xyz/backup.db")

    def test_snapshot_path(self, db):
        bm = BackupManager(db)
        path = bm.snapshot_path()
        assert path.startswith("mia_backup_")
        assert path.endswith(".db")