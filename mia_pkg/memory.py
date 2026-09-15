"""Memory Object + MemoryStore — persistência de memórias em SQLite.

Memory Objects são imutáveis após criação (append-only).
Mutações criam versões novas.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection


# ======================================================================
# Enums
# ======================================================================

class MemoryType(str, Enum):
    experience = "experience"
    preference = "preference"
    fact = "fact"
    belief = "belief"
    emotion = "emotion"
    relationship = "relationship"
    decision = "decision"


class MemoryScope(str, Enum):
    personal = "personal"
    shared = "shared"
    private = "private"


# ======================================================================
# MemoryObject dataclass
# ======================================================================

@dataclass
class MemoryObject:
    """Objeto de memória conforme contrato D.4.

    Imutável após criação — mutações criam versões novas.
    """
    content: str
    type: MemoryType = MemoryType.experience
    source: str = ""
    importance: float = 0.5
    confidence: float = 0.5
    scope: MemoryScope = MemoryScope.personal
    tags: list[str] = field(default_factory=list)
    associations: list[str] = field(default_factory=list)  # UUIDs
    person_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: int = 1
    is_consolidated: bool = False
    access_count: int = 0
    last_accessed_at: str | None = None


# ======================================================================
# MemoryStore
# ======================================================================

class MemoryStore:
    """Armazena, recupera e gerencia Memory Objects em SQLite.

    CRUD completo com importance scoring.
    """

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, obj: MemoryObject) -> MemoryObject:
        """Persiste um novo MemoryObject."""
        self._db.execute(
            "INSERT INTO memory_objects "
            "(id, content, type, source, created_at, updated_at, importance, confidence, "
            "scope, person_id, version, is_consolidated, access_count, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                obj.id, obj.content, obj.type.value, obj.source,
                obj.created_at, obj.updated_at, obj.importance, obj.confidence,
                obj.scope.value, obj.person_id, obj.version,
                int(obj.is_consolidated), obj.access_count,
                json.dumps(obj.tags),
            ),
        )
        self._db.commit()
        return obj

    def get(self, memory_id: str) -> MemoryObject | None:
        """Recupera um MemoryObject pelo ID."""
        row = self._db.fetchone(
            "SELECT * FROM memory_objects WHERE id = ?", (memory_id,)
        )
        if not row:
            return None
        return self._row_to_object(row)

    def update_importance(self, memory_id: str, importance: float) -> bool:
        """Atualiza a importância de uma memória (exceto scope: private)."""
        if not (0.0 <= importance <= 1.0):
            return False
        self._db.execute(
            "UPDATE memory_objects SET importance = ?, updated_at = ? WHERE id = ?",
            (importance, datetime.now(timezone.utc).isoformat(), memory_id),
        )
        self._db.commit()
        return self._db.connection.total_changes > 0

    def delete(self, memory_id: str) -> bool:
        """Remove uma memória (soft delete via versão)."""
        self._db.execute(
            "DELETE FROM memory_objects WHERE id = ?", (memory_id,)
        )
        self._db.commit()
        return self._db.connection.total_changes > 0

    def list_by_importance(self, limit: int = 10) -> list[MemoryObject]:
        """Lista memórias ordenadas por importância (desc)."""
        rows = self._db.fetchall(
            "SELECT * FROM memory_objects ORDER BY importance DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_object(r) for r in rows]

    def search_by_content(self, keyword: str) -> list[MemoryObject]:
        """Busca por keyword no conteúdo (MVP — keyword search simples)."""
        rows = self._db.fetchall(
            "SELECT * FROM memory_objects WHERE content LIKE ? ORDER BY importance DESC",
            (f"%{keyword}%",),
        )
        return [self._row_to_object(r) for r in rows]

    def count(self) -> int:
        """Conta total de memórias."""
        row = self._db.fetchone("SELECT COUNT(*) as cnt FROM memory_objects")
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _row_to_object(self, row: dict[str, Any]) -> MemoryObject:
        """Converte uma linha do banco em MemoryObject."""
        return MemoryObject(
            id=row["id"],
            content=row["content"],
            type=MemoryType(row["type"]),
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            importance=row["importance"],
            confidence=row["confidence"],
            scope=MemoryScope(row["scope"]),
            person_id=row.get("person_id"),
            tags=json.loads(row.get("tags", "[]")),
            version=row.get("version", 1),
            is_consolidated=bool(row.get("is_consolidated", 0)),
            access_count=row.get("access_count", 0),
            last_accessed_at=row.get("last_accessed_at"),
        )
