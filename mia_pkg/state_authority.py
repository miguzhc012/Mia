"""State Authority — ponto único de entrada para mudanças de estado.

    O LLM NUNCA escreve direto em estado protegido.
    O LLM apenas gera StateTransitionProposals.
    A StateAuthority orquestra PolicyEngine + StateEngine + Auditoria.

    Isso NÃO é norma de prompt — é arquitetura.
    Enforcement é físico: o runtime não expõe endpoint de escrita ao módulo LLM.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, Event, EventType
from mia_pkg.policy_engine import PolicyEngine, PolicyResult, StateTransitionProposal


# ======================================================================
# Result types
# ======================================================================

@dataclass
class ValidationResult:
    """Resultado da validação de schema/ranges."""
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class TransitionResult:
    """Resultado completo de uma tentativa de transição."""
    applied: bool = False
    transition_id: str | None = None
    validation: ValidationResult = field(default_factory=ValidationResult)
    policy: PolicyResult = field(default_factory=PolicyResult)
    snapshot_before: dict[str, Any] = field(default_factory=dict)
    snapshot_after: dict[str, Any] | None = None


# ======================================================================
# State Authority
# ======================================================================

class StateAuthority:
    """Ponto único de entrada. Orquestra PolicyEngine + Auditoria.

    Fluxo:
    1. Recebe proposal
    2. Verifica via PolicyEngine
    3. Valida ranges/schema (StateEngine interno)
    4. Aplica transição (determinístico)
    5. Registra em audit log (append-only)
    6. Emite evento STATE_CHANGED
    """

    # Ranges válidos para campos numéricos [0.0, 1.0]
    _RANGE_FIELDS: dict[str, tuple[float, float]] = {
        "happiness": (0.0, 1.0), "sadness": (0.0, 1.0),
        "anger": (0.0, 1.0), "fear": (0.0, 1.0),
        "surprise": (0.0, 1.0), "disgust": (0.0, 1.0),
        "trust_level": (0.0, 1.0), "anticipation": (0.0, 1.0),
        "curiosity_level": (0.0, 1.0), "loneliness": (0.0, 1.0),
        "affection": (0.0, 1.0), "boredom": (0.0, 1.0),
        "mood_valence": (-1.0, 1.0), "mood_arousal": (0.0, 1.0),
        "mood_dominance": (0.0, 1.0),
        "openness": (0.0, 1.0), "conscientiousness": (0.0, 1.0),
        "extraversion": (0.0, 1.0), "agreeableness": (0.0, 1.0),
        "neuroticism": (0.0, 1.0), "curiosity": (0.0, 1.0),
        "playfulness": (0.0, 1.0), "assertiveness": (0.0, 1.0),
        "empathy": (0.0, 1.0), "independence": (0.0, 1.0),
        "trust": (0.0, 1.0), "intimacy": (0.0, 1.0),
        "affinity": (0.0, 1.0), "familiarity": (0.0, 1.0),
        "importance": (0.0, 1.0), "confidence": (0.0, 1.0),
    }

    def __init__(
        self,
        db: SQLiteConnection,
        policy_engine: PolicyEngine,
        event_bus: EventBus | None = None,
    ) -> None:
        self._db = db
        self._policy = policy_engine
        self._event_bus = event_bus
        # Recupera o último hash da chain do banco (persistente entre processos)
        self._last_audit_hash: str = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Carrega o hash da última transição auditada (ou hash vazio se nenhuma)."""
        row = self._db.fetchone(
            "SELECT hash FROM state_transitions_audit ORDER BY rowid DESC LIMIT 1"
        )
        if row and row.get("hash"):
            return row["hash"]
        return "0" * 64

    def verify_chain(self) -> tuple[bool, int, list[str]]:
        """Verifica a integridade da hash chain do audit log.

        Returns:
            (ok, quantos_registros, lista_de_erros)
        """
        rows = self._db.fetchall(
            "SELECT id, target, key, before_snapshot, after_snapshot, "
            "hash, hash_prev FROM state_transitions_audit ORDER BY rowid ASC"
        )
        prev = "0" * 64
        errors: list[str] = []
        for i, row in enumerate(rows):
            payload = (
                f"{row['id']}:{row['target']}:{row['key']}:"
                f"{row['before_snapshot']}:{row['after_snapshot']}:{row['hash_prev']}"
            )
            calc = hashlib.sha256(payload.encode()).hexdigest()
            if row["hash_prev"] != prev:
                errors.append(f"Registro {i}: hash_prev não bate com o registro anterior")
            if row["hash"] != calc:
                errors.append(f"Registro {i}: hash corrente não confere com o payload")
            prev = row["hash"]
        return (len(errors) == 0, len(rows), errors)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def propose(self, proposal: StateTransitionProposal) -> TransitionResult:
        """Fluxo completo: validate -> policy check -> apply -> audit.

        Returns:
            TransitionResult com detalhes da operação.
        """
        # Snapshot antes
        snapshot_before = self._take_snapshot(proposal.target)

        # 1. Policy check
        policy_result = self._policy.check(proposal, snapshot_before)
        if not policy_result.allowed:
            return TransitionResult(
                applied=False,
                validation=ValidationResult(valid=True),
                policy=policy_result,
                snapshot_before=snapshot_before,
            )

        # 2. State validation (ranges/schema)
        validation = self._validate(proposal)

        # 3. Apply (se válido)
        if not validation.valid:
            return TransitionResult(
                applied=False,
                validation=validation,
                policy=policy_result,
                snapshot_before=snapshot_before,
            )

        # Aplica a mudança
        self._apply_transition(proposal, snapshot_before)
        snapshot_after = self._take_snapshot(proposal.target)

        # 4. Audit
        transition_id = str(uuid.uuid4())
        self._audit(proposal, snapshot_before, snapshot_after, transition_id)

        # 5. Event
        if self._event_bus:
            self._event_bus.emit(Event(
                type=EventType.MIGUEL_SPOKE,  # Placeholder — futuro: STATE_CHANGED
                source="state_authority",
                payload={
                    "target": proposal.target,
                    "key": proposal.key,
                    "before": snapshot_before,
                    "after": snapshot_after,
                    "transition_id": transition_id,
                },
            ))

        return TransitionResult(
            applied=True,
            transition_id=transition_id,
            validation=validation,
            policy=policy_result,
            snapshot_before=snapshot_before,
            snapshot_after=snapshot_after,
        )

    def get_state(self) -> dict[str, Any]:
        """Retorna snapshot do estado atual."""
        state: dict[str, Any] = {}
        for table in ["emotion_state", "personality_state", "identity_state"]:
            row = self._db.fetchone(f"SELECT * FROM {table} ORDER BY snapshot_at DESC LIMIT 1")
            if row:
                state[table] = row
        return state

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    # Colunas permitidas por target (whitelist — NUNCA interpolar chave sem passar aqui)
    _TARGET_COLUMNS: dict[str, set[str]] = {
        "emotion": {"happiness", "sadness", "anger", "fear", "anxiety", "enthusiasm",
                    "affection", "attachment", "curiosity", "jealousy", "passion", "interest"},
        "personality": {"openness", "conscientiousness", "extraversion", "agreeableness",
                        "neuroticism", "patience", "sociability", "humor", "spontaneity",
                        "warmth", "sassiness"},
        "identity": {"name", "self_model", "core_values", "beliefs", "narrative_identity"},
        "relationship": {"familiarity", "trust", "respect", "affection", "attachment",
                         "admiration", "attraction", "intimacy", "comfort", "tension",
                         "insecurity", "safety", "expectation"},
        "person": {"name", "role", "notes", "status"},
        "goal": {"title", "description", "status", "priority", "progress"},
        "diary": {"content", "mood", "reflection"},
    }

    _RANGE_FIELDS: dict[str, tuple[float, float]] = {
        "happiness": (-1.0, 1.0),
        "sadness": (0.0, 1.0),
        "anger": (0.0, 1.0),
        "fear": (0.0, 1.0),
        "anxiety": (0.0, 1.0),
        "enthusiasm": (0.0, 1.0),
        "affection": (-1.0, 1.0),
        "attachment": (0.0, 1.0),
        "curiosity": (0.0, 1.0),
        "jealousy": (0.0, 1.0),
        "passion": (0.0, 1.0),
        "interest": (0.0, 1.0),
    }

    def _validate(self, proposal: StateTransitionProposal) -> ValidationResult:
        """State Engine interno: valida ranges, schema e whitelist de colunas."""
        errors: list[str] = []

        # WHITELIST de colunas por target — bloqueia SQL injection e keys arbitrárias
        allowed = self._TARGET_COLUMNS.get(proposal.target, set())
        if proposal.target not in ("memory",) and proposal.key not in allowed:
            errors.append(
                f"Chave '{proposal.key}' não é permitida para target '{proposal.target}'."
            )
            return ValidationResult(valid=False, errors=errors)

        if proposal.key in self._RANGE_FIELDS:
            low, high = self._RANGE_FIELDS[proposal.key]
            if isinstance(proposal.delta, (int, float)):
                if not (low <= proposal.delta <= high):
                    errors.append(
                        f"Valor {proposal.delta} fora do range [{low}, {high}] "
                        f"para campo '{proposal.key}'."
                    )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _apply_transition(self, proposal: StateTransitionProposal, before: dict[str, Any]) -> None:
        """Aplica a transição de forma determinística.

        NOTA: proposal.key SÓ é interpolado após passar pela whitelist
        _TARGET_COLUMNS em _validate(). Para targets sem whitelist
        (memory), key é tratado como dado simples.
        """
        now = datetime.now(timezone.utc).isoformat()
        target_table = {
            "emotion": "emotion_state",
            "personality": "personality_state",
            "identity": "identity_state",
            "relationship": "relationships",
            "person": "people",
            "goal": "goals",
            "diary": "diary",
        }.get(proposal.target)

        # Memória: create/update (key = tipo da memória, delta = conteúdo)
        if proposal.target == "memory":
            if proposal.action == "create":
                row_id = str(uuid.uuid4())
                self._db.execute(
                    "INSERT INTO memory_objects (id, content, type, source, created_at, updated_at, importance) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (row_id, str(proposal.delta), proposal.key, proposal.source, now, now, proposal.confidence),
                )
            elif before:
                self._db.execute(
                    "UPDATE memory_objects SET content = ?, updated_at = ?, importance = ? WHERE id = ?",
                    (str(proposal.delta), now, proposal.confidence, before.get("id")),
                )
            self._db.commit()
            return

        # Demais targets: key validado por whitelist em _validate()
        if target_table is None or proposal.key not in self._TARGET_COLUMNS.get(proposal.target, set()):
            self._db.commit()  # transição registrada no audit, sem efeito colateral
            return

        if proposal.action in ("create", "add"):
            row_id = str(uuid.uuid4())
            # relações/pessoas/goals precisam de chave estrangeira (pessoa)
            if proposal.target == "relationship":
                self._db.execute(
                    f"INSERT INTO {target_table} (id, {proposal.key}, person_id, snapshot_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (row_id, proposal.delta, proposal.ref_id or "", now, now),
                )
            elif proposal.target in ("person", "goal"):
                self._db.execute(
                    f"INSERT INTO {target_table} (id, {proposal.key}, snapshot_at, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (row_id, proposal.delta, now, now),
                )
            else:
                self._db.execute(
                    f"INSERT INTO {target_table} (id, {proposal.key}, snapshot_at) VALUES (?, ?, ?)",
                    (row_id, proposal.delta, now),
                )
        elif before:
            # UPDATE no registro atual (snapshot mais recente)
            self._db.execute(
                f"UPDATE {target_table} SET {proposal.key} = ?, updated_at = ? WHERE id = ?",
                (proposal.delta, now, before["id"]),
            )

        self._db.commit()

    def _take_snapshot(self, target: str) -> dict[str, Any]:
        """Captura snapshot do estado para auditoria."""
        table_map = {
            "emotion": "emotion_state",
            "personality": "personality_state",
            "identity": "identity_state",
        }
        table = table_map.get(target)
        if table:
            row = self._db.fetchone(f"SELECT * FROM {table} ORDER BY snapshot_at DESC LIMIT 1")
            return row or {}
        return {}

    def _audit(
        self,
        proposal: StateTransitionProposal,
        before: dict[str, Any],
        after: dict[str, Any],
        transition_id: str,
    ) -> None:
        """Registra na tabela append-only de auditoria com hash chain."""
        now = datetime.now(timezone.utc).isoformat()
        before_json = json.dumps(before, default=str)
        after_json = json.dumps(after, default=str)

        # Hash chain
        payload = f"{transition_id}:{proposal.target}:{proposal.key}:{before_json}:{after_json}:{self._last_audit_hash}"
        current_hash = hashlib.sha256(payload.encode()).hexdigest()

        self._db.execute(
            "INSERT INTO state_transitions_audit "
            "(id, timestamp, component_origin, transition_type, target, key, "
            "before_snapshot, after_snapshot, evidence, confidence, "
            "applied_by, proposal_id, hash, hash_prev) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                transition_id,
                now,
                proposal.source,
                proposal.action,
                proposal.target,
                proposal.key,
                before_json,
                after_json,
                proposal.evidence,
                proposal.confidence,
                proposal.source,  # applied_by
                transition_id,   # proposal_id
                current_hash,    # hash
                self._last_audit_hash,
            ),
        )
        self._db.commit()
        self._last_audit_hash = current_hash
