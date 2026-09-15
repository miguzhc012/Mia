"""Memory Store — persistência de memórias (spec D.5).

- memory_objects: content, type, source, created_at, updated_at, importance, confidence, scope, person_id, embedding, emotional_context, provenance, decay_state, status, revision_history, observed_at, version, is_consolidated, access_count, last_accessed_at, tags
- memory_associations: memory_id, associated_id
- memory_retrieval: query, results
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
# Dataclasses — conforme spec D.5
# ======================================================================

@dataclass
class MemoryObject:
    """Objeto de memória conforme spec D.5."""
    content: str = ""
    type: str = "experience"
    source: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    importance: float = 0.5
    confidence: float = 0.5
    scope: str = "personal"
    person_id: str | None = None
    embedding: str | None = None
    emotional_context: str | None = None
    provenance: str | None = None
    decay_state: str = "active"
    status: str = "active"
    revision_history: str | None = None
    observed_at: str | None = None
    version: int = 1
    is_consolidated: int = 0
    access_count: int = 0
    last_accessed_at: str | None = None
    tags: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryAssociation:
    """Associação entre memórias (spec D.5)."""
    memory_id: str
    associated_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryRetrieval:
    """Resultado da busca de memórias (spec D.5)."""
    query: str
    results: list[MemoryObject]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ======================================================================
# Memory Store
# ======================================================================

class MemoryStore:
    """Gerencia memórias persistentes."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def create(self, obj: MemoryObject) -> MemoryObject:
        """Cria uma nova memória."""
        tags_val = self._json_if_needed(obj.tags)
        type_val = obj.type.value if hasattr(obj.type, 'value') else obj.type
        self._db.execute(
            """INSERT INTO memory_objects
               (id, content, type, source, created_at, updated_at, importance,
                confidence, scope, person_id, embedding, emotional_context,
                provenance, decay_state, status, revision_history, observed_at,
                version, is_consolidated, access_count, last_accessed_at, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                obj.id,
                obj.content,
                type_val,
                obj.source,
                obj.created_at,
                obj.updated_at,
                obj.importance,
                obj.confidence,
                obj.scope,
                obj.person_id,
                self._json_if_needed(obj.embedding),
                self._json_if_needed(obj.emotional_context),
                self._json_if_needed(obj.provenance),
                obj.decay_state,
                self._json_if_needed(obj.status),
                self._json_if_needed(obj.revision_history),
                obj.observed_at,
                obj.version,
                obj.is_consolidated,
                obj.access_count,
                obj.last_accessed_at,
                tags_val,
            ),
        )
        self._db.commit()
        return obj

    @staticmethod
    def _json_if_needed(value: Any) -> Any:
        """Serializa dict/list para JSON; deixa tipos primitivos como estão."""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)
        return value

    def get(self, obj_id: str) -> MemoryObject | None:
        """Recupera uma memória por ID."""
        row = self._db.fetchone(
            "SELECT * FROM memory_objects WHERE id = ?", (obj_id,)
        )
        return self._row_to_obj(row) if row else None

    def update(self, obj: MemoryObject) -> MemoryObject:
        """Atualiza uma memória."""
        self._db.execute(
            """UPDATE memory_objects
               SET content = ?, type = ?, source = ?, created_at = ?, updated_at = ?, importance = ?,
                confidence = ?, scope = ?, person_id = ?, embedding = ?, emotional_context = ?,
                provenance = ?, decay_state = ?, status = ?, revision_history = ?, observed_at = ?,
                version = ?, is_consolidated = ?, access_count = ?, last_accessed_at = ?, tags = ?
               WHERE id = ?""",
            (
                obj.content,
                obj.type,
                obj.source,
                obj.created_at,
                obj.updated_at,
                obj.importance,
                obj.confidence,
                obj.scope,
                obj.person_id,
                obj.embedding,
                obj.emotional_context,
                obj.provenance,
                obj.decay_state,
                obj.status,
                obj.revision_history,
                obj.observed_at,
                obj.version,
                obj.is_consolidated,
                obj.access_count,
                obj.last_accessed_at,
                obj.tags,
                obj.id,
            ),
        )
        self._db.commit()
        return obj

    def delete(self, obj_id: str) -> None:
        """Remove uma memória."""
        self._db.execute("DELETE FROM memory_objects WHERE id = ?", (obj_id,))
        self._db.commit()

    def recall(self, query: str, scope: str = "personal", limit: int = 5) -> MemoryRetrieval:
        """Recupera memórias relevantes."""
        # TODO: implementar busca com embeddings
        rows = self._db.fetchall(
            "SELECT * FROM memory_objects WHERE content LIKE ? AND scope = ? ORDER BY importance DESC LIMIT ?",
            (f"%{query}%", scope, limit),
        )
        results = [MemoryObject(**r) for r in rows]
        return MemoryRetrieval(query=query, results=results)

    def update_importance(self, obj_id: str, importance: float) -> bool:
        """Atualiza a importância de uma memória. False se inválida ou inexistente."""
        if not (0.0 <= importance <= 1.0):
            return False
        row = self._db.fetchone(
            "SELECT id FROM memory_objects WHERE id = ?", (obj_id,)
        )
        if not row:
            return False
        self._db.execute(
            "UPDATE memory_objects SET importance = ?, updated_at = ? WHERE id = ?",
            (
                importance,
                datetime.now(timezone.utc).isoformat(),
                obj_id,
            ),
        )
        self._db.commit()
        return True

    def list_by_importance(self, limit: int = 10) -> list[MemoryObject]:
        """Lista memórias por importância (descendente)."""
        rows = self._db.fetchall(
            "SELECT * FROM memory_objects ORDER BY importance DESC LIMIT ?",
            (limit,),
        )
        return [MemoryObject(**r) for r in rows]

    def search_by_content(self, query: str) -> list[MemoryObject]:
        """Busca memórias por keyword no conteúdo."""
        rows = self._db.fetchall(
            "SELECT * FROM memory_objects WHERE content LIKE ? ORDER BY importance DESC",
            (f"%{query}%",),
        )
        return [MemoryObject(**r) for r in rows]

    def count(self) -> int:
        """Retorna o total de memórias."""
        row = self._db.fetchone("SELECT COUNT(*) AS n FROM memory_objects")
        return int(row["n"]) if row else 0

    def _row_to_obj(self, row: dict[str, Any]) -> MemoryObject:
        """Converte row do banco para MemoryObject."""
        def _unjson(value: Any) -> Any:
            """Deserializa JSON se for string JSON; senão retorna como está."""
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
            return value

        tags_val = _unjson(row["tags"]) if row.get("tags") else []
        return MemoryObject(
            content=row["content"],
            type=row["type"],
            source=row["source"],
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            importance=row["importance"],
            confidence=row["confidence"],
            scope=row["scope"],
            person_id=row["person_id"],
            embedding=_unjson(row["embedding"]),
            emotional_context=_unjson(row["emotional_context"]),
            provenance=_unjson(row["provenance"]),
            decay_state=row["decay_state"],
            status=_unjson(row["status"]),
            revision_history=_unjson(row["revision_history"]),
            observed_at=row["observed_at"],
            version=row["version"],
            is_consolidated=row["is_consolidated"],
            access_count=row["access_count"],
            last_accessed_at=row["last_accessed_at"],
            tags=tags_val,
        )
