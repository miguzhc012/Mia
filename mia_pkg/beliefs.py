"""Belief — ciclo de vida de crenças conforme §21 do onboarding v2.

Ciclo: OBSERVAÇÃO → HIPÓTESE → CRENÇA → NOVA EVIDÊNCIA → CONFIRMAÇÃO/CONTRADIÇÃO → REVISÃO.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection


class BeliefStatus(str, Enum):
    active = "active"
    revised = "revised"
    rejected = "rejected"
    disputed = "disputed"


@dataclass
class Belief:
    """Crença da Mia conforme §21 do onboarding."""
    proposition: str
    confidence: float = 0.5
    source_evidence: str = ""
    person_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: BeliefStatus = BeliefStatus.active
    revision_history: list[dict[str, Any]] = field(default_factory=list)


class BeliefStore:
    """Persistência e ciclo de vida de crenças."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def create(self, belief: Belief) -> Belief:
        """Cria uma nova crença."""
        self._db.execute(
            """INSERT INTO beliefs
               (id, proposition, confidence, source_evidence,
                created_at, updated_at, status, revision_history, person_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                belief.id,
                belief.proposition,
                belief.confidence,
                belief.source_evidence,
                belief.created_at,
                belief.updated_at,
                belief.status.value,
                json.dumps(belief.revision_history),
                belief.person_id,
            ),
        )
        self._db.commit()
        return belief

    def increase_confidence(self, belief_id: str, amount: float, evidence: str = "") -> Belief | None:
        """Aumenta a confiança de uma crença."""
        b = self.get(belief_id)
        if not b:
            return None
        new_conf = min(1.0, b.confidence + amount)
        return self._update_confidence(b, new_conf, evidence)

    def decrease_confidence(self, belief_id: str, amount: float, evidence: str = "") -> Belief | None:
        """Reduz a confiança de uma crença."""
        b = self.get(belief_id)
        if not b:
            return None
        new_conf = max(0.0, b.confidence - amount)
        return self._update_confidence(b, new_conf, evidence)

    def revise(self, belief_id: str, new_proposition: str, new_confidence: float, reason: str = "") -> Belief | None:
        """Revisa uma crença (muda a proposição)."""
        b = self.get(belief_id)
        if not b:
            return None
        now = datetime.now(timezone.utc).isoformat()
        revision = {
            "old_proposition": b.proposition,
            "old_confidence": b.confidence,
            "new_proposition": new_proposition,
            "new_confidence": new_confidence,
            "reason": reason,
            "timestamp": now,
        }
        history = b.revision_history + [revision]
        self._db.execute(
            """UPDATE beliefs
               SET proposition=?, confidence=?, status='revised',
                   revision_history=?, updated_at=?
               WHERE id=?""",
            (new_proposition, new_confidence, json.dumps(history), now, belief_id),
        )
        self._db.commit()
        return self.get(belief_id)

    def reject(self, belief_id: str, reason: str = "") -> Belief | None:
        """Rejeita uma crença."""
        b = self.get(belief_id)
        if not b:
            return None
        now = datetime.now(timezone.utc).isoformat()
        revision = {
            "action": "rejected",
            "old_proposition": b.proposition,
            "old_confidence": b.confidence,
            "reason": reason,
            "timestamp": now,
        }
        history = b.revision_history + [revision]
        self._db.execute(
            """UPDATE beliefs
               SET status='rejected', revision_history=?, updated_at=?
               WHERE id=?""",
            (json.dumps(history), now, belief_id),
        )
        self._db.commit()
        return self.get(belief_id)

    def get(self, belief_id: str) -> Belief | None:
        """Recupera uma crença por ID."""
        row = self._db.fetchone(
            "SELECT * FROM beliefs WHERE id=?", (belief_id,)
        )
        if not row:
            return None
        return self._row_to_belief(row)

    def list_active(self, limit: int = 50) -> list[Belief]:
        """Lista crenças ativas."""
        rows = self._db.fetchall(
            "SELECT * FROM beliefs WHERE status='active' ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_belief(r) for r in rows]

    def _update_confidence(self, b: Belief, new_conf: float, evidence: str) -> Belief:
        now = datetime.now(timezone.utc).isoformat()
        revision = {
            "old_confidence": b.confidence,
            "new_confidence": new_conf,
            "evidence": evidence,
            "timestamp": now,
        }
        history = b.revision_history + [revision]
        self._db.execute(
            """UPDATE beliefs
               SET confidence=?, revision_history=?, updated_at=?
               WHERE id=?""",
            (new_conf, json.dumps(history), now, b.id),
        )
        self._db.commit()
        return self.get(b.id)

    def _row_to_belief(self, row: dict) -> Belief:
        return Belief(
            id=row["id"],
            proposition=row["proposition"],
            confidence=row["confidence"],
            source_evidence=row.get("source_evidence", ""),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=BeliefStatus(row["status"]),
            revision_history=json.loads(row.get("revision_history", "[]") or "[]"),
            person_id=row.get("person_id"),
        )
