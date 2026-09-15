"""Monitoring — dashboard de saúde / coleta de métricas.

Fase 16: coleta métricas do DB e componentes, expõe health summary.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mia_pkg.db import SQLiteConnection


@dataclass
class HealthReport:
    """Relatório de saúde do sistema."""
    timestamp: float = field(default_factory=time.time)
    db_ok: bool = True
    tables: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    latencies_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "db_ok": self.db_ok,
            "tables": self.tables,
            "issues": self.issues,
            "latencies_ms": self.latencies_ms,
        }


class HealthMonitor:
    """Coleta métricas de saúde do sistema."""

    TABLE_NAMES = [
        "identity_state", "personality_state", "emotion_state",
        "memory_objects", "memory_associations", "beliefs", "needs", "desires",
        "attention_log", "events", "state_transitions_audit",
        "people", "relationships", "relationship_events",
        "goals", "diary", "sensations", "sandbox_actions", "sessions",
    ]

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def health_check(self) -> HealthReport:
        report = HealthReport()

        # 1. DB acessível?
        try:
            row = self._db.fetchone("SELECT 1 AS ok")
            report.db_ok = bool(row and row.get("ok") == 1)
        except Exception as e:
            report.db_ok = False
            report.issues.append(f"db: {e}")
            return report

        # 2. Contagem de cada tabela
        for table in self.TABLE_NAMES:
            try:
                row = self._db.fetchone(f"SELECT COUNT(*) AS n FROM {table}")
                report.tables[table] = row["n"] if row else 0
            except Exception:
                pass  # tabela pode não existir ainda

        # 3. Issues: estado sem identidade? memórias demais?
        if report.tables.get("memory_objects", 0) > 1000:
            report.issues.append("memórias > 1000: considerar consolidação")
        if report.tables.get("events", 0) > 5000:
            report.issues.append("events > 5000: considerar arquivamento")

        return report

    def measure_latency(self, fn, *args, label: str = "op", **kwargs) -> float:
        """Mede latência de uma operação (ms)."""
        start = time.monotonic()
        fn(*args, **kwargs)
        elapsed = (time.monotonic() - start) * 1000.0
        return round(elapsed, 2)

    def component_status(self) -> dict[str, str]:
        """Status de cada componente (imports funcionam?)."""
        status: dict[str, str] = {}
        components = [
            "affective_engine", "attention_policy", "autonomy", "avatar",
            "belief_revision", "beliefs", "chat", "cli",
            "cognitive_core", "config", "consolidation",
            "context_assembly", "db", "distributed", "emotion_governor", "events",
            "evolution", "identity", "identity_authority", "llm",
            "memory", "monitoring", "needs_desires", "perception", "reflection",
            "security", "social", "state_authority", "voice", "world", "agents",
        ]
        import importlib
        for mod in components:
            try:
                importlib.import_module(f"mia_pkg.{mod}")
                status[mod] = "ok"
            except Exception as e:
                status[mod] = f"error: {e}"
        return status


# ======================================================================
# Backup / Restore
# ======================================================================

class BackupManager:
    """Snapshot completo do SQLite + restore.

    Fase 16: backup usa SQLite backup API (consistente mesmo com
    conexão ativa). Restore recarrega o arquivo.
    """

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def backup_to(self, path: str) -> bool:
        """Copia o DB para um arquivo (consistente via backup API)."""
        import sqlite3
        try:
            dest = sqlite3.connect(path)
            with dest:
                self._db.connection.backup(dest)
            dest.close()
            return True
        except Exception:
            return False

    def restore_from(self, path: str) -> bool:
        """Restaura o DB a partir de um arquivo de backup.

        AVISO: substitui os dados atuais (in-memory ou arquivo).
        """
        import sqlite3
        try:
            src = sqlite3.connect(path)
            with self._db.connection:
                src.backup(self._db.connection)
            src.close()
            return True
        except Exception:
            return False

    def snapshot_path(self, prefix: str = "mia_backup") -> str:
        """Gera caminho de snapshot com timestamp."""
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{ts}.db"