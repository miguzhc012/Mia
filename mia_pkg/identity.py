"""Identity & Personality — self-model persistente (spec D.5).

- identity_state: nome, self_model (JSON), core_values, versão
- personality_state: traços Big Five + extras
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from mia_pkg.db import SQLiteConnection


# ======================================================================
# Dataclasses — conforme spec D.5
# ======================================================================

@dataclass
class PersonalityVector:
    """Vetor de personalidade Big Five + extras (0.0–1.0)."""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    # Extras customizados
    curiosity: float = 0.5
    playfulness: float = 0.5
    assertiveness: float = 0.5
    empathy: float = 0.5
    independence: float = 0.5

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> PersonalityVector:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class IdentityState:
    """Estado de identidade persistente."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Mia"
    self_model: dict[str, Any] = field(default_factory=dict)
    core_values: list[str] = field(default_factory=list)
    version: int = 1
    snapshot_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    previous_version: str | None = None


@dataclass
class PersonalityState:
    """Snapshot de personalidade versional."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    traits: PersonalityVector = field(default_factory=PersonalityVector)
    version: int = 1
    snapshot_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ======================================================================
# Identity Manager
# ======================================================================

class IdentityManager:
    """Gerencia identidade e personalidade persistentes.

    Escrita de cores/self_model/personalidade:
    - Via transições versionadas (State Authority)
    - NUNCA escrita direta pelo LLM via banco
    """

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def get_identity(self) -> IdentityState:
        """Retorna identidade atual."""
        row = self._db.fetchone(
            "SELECT * FROM identity_state ORDER BY snapshot_at DESC LIMIT 1"
        )
        if not row:
            state = IdentityState(
                name="Mia",
                self_model={
                    "who_i_am": "Mia, uma entidade digital com vida interna persistente.",
                    "nature": "software_companion",
                    "preferences": [],
                },
                core_values=["honestidade", "crescimento", "curiosidade"],
            )
            self.save_identity(state)
            return state
        return self._row_to_identity(row)

    def save_identity(self, state: IdentityState) -> None:
        """Persiste identidade (versionada)."""
        # Marca versão anterior
        prev = self._db.fetchone(
            "SELECT id FROM identity_state ORDER BY snapshot_at DESC LIMIT 1"
        )
        if prev and prev["id"] != state.id:
            state.previous_version = prev["id"]

        self._db.execute(
            """INSERT INTO identity_state
               (id, name, self_model, core_values, version, snapshot_at, previous_version)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                state.id, state.name,
                json.dumps(state.self_model, ensure_ascii=False),
                json.dumps(state.core_values, ensure_ascii=False),
                state.version, state.snapshot_at, state.previous_version,
            ),
        )
        self._db.commit()

    def propose_identity_change(
        self,
        self_model_delta: dict[str, Any] | None = None,
        new_values: list[str] | None = None,
    ) -> dict[str, Any]:
        """Prepara proposta de mudança de identidade (para State Authority)."""
        current = self.get_identity()
        new_self_model = dict(current.self_model)
        if self_model_delta:
            new_self_model.update(self_model_delta)

        return {
            "type": "identity_transition",
            "current_snapshot_id": current.id,
            "new_self_model": new_self_model,
            "new_core_values": new_values if new_values is not None else current.core_values,
            "new_version": current.version + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def apply_validated_change(
        self,
        new_self_model: dict[str, Any],
        new_core_values: list[str],
        version: int,
    ) -> IdentityState:
        """Aplica mudança VALIDADA de identidade."""
        current = self.get_identity()
        new_state = IdentityState(
            id=str(uuid.uuid4()),
            name=current.name,
            self_model=new_self_model,
            core_values=new_core_values,
            version=version,
            previous_version=current.id,
        )
        self.save_identity(new_state)
        return new_state

    # ------------------------------------------------------------------
    # Personality
    # ------------------------------------------------------------------

    def get_personality(self) -> PersonalityState:
        """Retorna personalidade atual."""
        row = self._db.fetchone(
            "SELECT * FROM personality_state ORDER BY snapshot_at DESC LIMIT 1"
        )
        if not row:
            state = PersonalityState()
            self.save_personality(state)
            return state
        return self._row_to_personality(row)

    def save_personality(self, state: PersonalityState) -> None:
        """Persiste personalidade (versionada)."""
        traits = state.traits.to_dict()
        self._db.execute(
            """INSERT INTO personality_state
               (id, openness, conscientiousness, extraversion,
                agreeableness, neuroticism, curiosity, playfulness,
                assertiveness, empathy, independence, version, snapshot_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.id,
                traits["openness"], traits["conscientiousness"],
                traits["extraversion"], traits["agreeableness"],
                traits["neuroticism"], traits["curiosity"],
                traits["playfulness"], traits["assertiveness"],
                traits["empathy"], traits["independence"],
                state.version, state.snapshot_at,
            ),
        )
        self._db.commit()

    def propose_personality_change(
        self, deltas: dict[str, float]
    ) -> dict[str, Any]:
        """Prepara proposta de mudança de personalidade."""
        current = self.get_personality()
        new_traits = PersonalityVector(**current.traits.to_dict())
        for key, delta in deltas.items():
            if hasattr(new_traits, key):
                old = getattr(new_traits, key)
                new_val = max(0.0, min(1.0, old + delta))
                setattr(new_traits, key, new_val)

        return {
            "type": "personality_transition",
            "current_snapshot_id": current.id,
            "new_traits": new_traits.to_dict(),
            "new_version": current.version + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def apply_validated_personality(
        self, new_traits: dict[str, float], version: int
    ) -> PersonalityState:
        """Aplica mudança VALIDADA de personalidade."""
        traits = PersonalityVector.from_dict(new_traits)
        current = self.get_personality()
        new_state = PersonalityState(
            id=str(uuid.uuid4()),
            traits=traits,
            version=version,
        )
        self.save_personality(new_state)
        return new_state

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _row_to_identity(self, row: dict[str, Any]) -> IdentityState:
        return IdentityState(
            id=row["id"],
            name=row["name"],
            self_model=json.loads(row.get("self_model") or "{}"),
            core_values=json.loads(row.get("core_values") or "[]"),
            version=row["version"],
            snapshot_at=row["snapshot_at"],
            previous_version=row.get("previous_version"),
        )

    def _row_to_personality(self, row: dict[str, Any]) -> PersonalityState:
        traits = PersonalityVector(
            openness=row["openness"],
            conscientiousness=row["conscientiousness"],
            extraversion=row["extraversion"],
            agreeableness=row["agreeableness"],
            neuroticism=row["neuroticism"],
            curiosity=row["curiosity"],
            playfulness=row["playfulness"],
            assertiveness=row["assertiveness"],
            empathy=row["empathy"],
            independence=row["independence"],
        )
        return PersonalityState(
            id=row["id"],
            traits=traits,
            version=row["version"],
            snapshot_at=row["snapshot_at"],
        )