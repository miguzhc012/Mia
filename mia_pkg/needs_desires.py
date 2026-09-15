"""Needs & Desires — framework afetivo conforme §16 do onboarding v2.

NEED ≠ DESIRE ≠ GOAL ≠ EMOTION ≠ SENSATION.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection


class NeedType(str, Enum):
    social_interaction = "social_interaction"
    attention = "attention"
    rest = "rest"
    stimulation = "stimulation"
    safety = "safety"
    novelty = "novelty"
    exploration = "exploration"
    achievement = "achievement"


class DesireType(str, Enum):
    interaction = "interaction"
    exploration = "exploration"
    creation = "creation"
    discovery = "discovery"


@dataclass
class Need:
    """Necessidade da Mia — condição que influencia motivação."""
    need_type: NeedType
    intensity: float = 0.5
    satisfied: bool = False
    person_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_fulfilled_at: str | None = None


@dataclass
class Desire:
    """Desejo da Mia — aquilo que gostaria de experimentar/obter/fazer."""
    description: str
    desire_type: DesireType | None = None
    priority: float = 0.5
    fulfilled: bool = False
    goal_id: str | None = None
    person_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class NeedsDesiresStore:
    """Persistência e ciclo de vida de necessidades e desejos."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    # --- Needs ---

    def create_need(self, need: Need) -> Need:
        self._db.execute(
            """INSERT INTO needs
               (id, need_type, intensity, satisfied, created_at, updated_at,
                last_fulfilled_at, person_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                need.id,
                need.need_type.value,
                need.intensity,
                1 if need.satisfied else 0,
                need.created_at,
                need.updated_at,
                need.last_fulfilled_at,
                need.person_id,
            ),
        )
        self._db.commit()
        return need

    def fulfill_need(self, need_id: str) -> Need | None:
        row = self._db.fetchone("SELECT * FROM needs WHERE id=?", (need_id,))
        if not row:
            return None
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "UPDATE needs SET satisfied=1, last_fulfilled_at=?, updated_at=? WHERE id=?",
            (now, now, need_id),
        )
        self._db.commit()
        return self._need_from_row(self._db.fetchone("SELECT * FROM needs WHERE id=?", (need_id,)))

    def list_unfulfilled(self, limit: int = 20) -> list[Need]:
        rows = self._db.fetchall(
            "SELECT * FROM needs WHERE satisfied=0 ORDER BY intensity DESC LIMIT ?",
            (limit,),
        )
        return [self._need_from_row(r) for r in rows]

    def list_unfulfilled_needs(self, limit: int = 20) -> list[Need]:
        """Lista necessidades não satisfeitas (alias de list_unfulfilled)."""
        return self.list_unfulfilled(limit)

    def list_unfulfilled_desires(self, limit: int = 20) -> list[Desire]:
        """Lista desejos não satisfeitos."""
        rows = self._db.fetchall(
            "SELECT * FROM desires WHERE fulfilled=0 ORDER BY priority DESC LIMIT ?",
            (limit,),
        )
        return [self._desire_from_row(r) for r in rows]

    def get_need(self, need_id: str) -> Need | None:
        row = self._db.fetchone("SELECT * FROM needs WHERE id=?", (need_id,))
        return self._need_from_row(row) if row else None

    def _need_from_row(self, row: dict[str, Any]) -> Need:
        return Need(
            id=row["id"],
            need_type=NeedType(row["need_type"]),
            intensity=row["intensity"],
            satisfied=bool(row["satisfied"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_fulfilled_at=row.get("last_fulfilled_at"),
            person_id=row.get("person_id"),
        )

    # --- Desires ---

    def create_desire(self, desire: Desire) -> Desire:
        self._db.execute(
            """INSERT INTO desires
               (id, description, desire_type, priority, fulfilled,
                created_at, updated_at, goal_id, person_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                desire.id,
                desire.description,
                desire.desire_type.value if desire.desire_type else None,
                desire.priority,
                1 if desire.fulfilled else 0,
                desire.created_at,
                desire.updated_at,
                desire.goal_id,
                desire.person_id,
            ),
        )
        self._db.commit()
        return desire

    def fulfill_desire(self, desire_id: str) -> Desire | None:
        row = self._db.fetchone("SELECT * FROM desires WHERE id=?", (desire_id,))
        if not row:
            return None
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "UPDATE desires SET fulfilled=1, updated_at=? WHERE id=?",
            (now, desire_id),
        )
        self._db.commit()
        return self._desire_from_row(self._db.fetchone("SELECT * FROM desires WHERE id=?", (desire_id,)))

    def _list_unfulfilled_desires(self, limit: int = 20) -> list[Desire]:
        rows = self._db.fetchall(
            "SELECT * FROM desires WHERE fulfilled=0 ORDER BY priority DESC LIMIT ?",
            (limit,),
        )
        return [self._desire_from_row(r) for r in rows]

    def get_desire(self, desire_id: str) -> Desire | None:
        row = self._db.fetchone("SELECT * FROM desires WHERE id=?", (desire_id,))
        return self._desire_from_row(row) if row else None

    def _desire_from_row(self, row: dict[str, Any]) -> Desire:
        dt = row.get("desire_type")
        return Desire(
            id=row["id"],
            description=row["description"],
            desire_type=DesireType(dt) if dt else None,
            priority=row["priority"],
            fulfilled=bool(row["fulfilled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            goal_id=row.get("goal_id"),
            person_id=row.get("person_id"),
        )
