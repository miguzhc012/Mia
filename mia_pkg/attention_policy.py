"""Attention / Initiative Policy — §26 do onboarding v2.

Recebe eventos e decide: ACT / WAIT / IGNORE.

Avalia: relevance, urgency, importance, context, current_activity,
user_availability, social_setting, internal_state, goals.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection


class AttentionDecision(str, Enum):
    ACT = "ACT"
    WAIT = "WAIT"
    IGNORE = "IGNORE"


@dataclass
class AttentionEvaluation:
    """Avaliação de um evento pela política de atenção."""
    event_type: str
    event_id: str | None = None
    relevance: float = 0.5
    urgency: float = 0.0
    importance: float = 0.5
    context: dict[str, Any] = field(default_factory=dict)
    current_activity: str | None = None
    user_available: bool = True
    social_setting: str | None = None
    internal_state: dict[str, Any] = field(default_factory=dict)
    active_goals: list[str] = field(default_factory=list)
    decision: AttentionDecision = AttentionDecision.IGNORE
    reasoning: str = ""


class AttentionPolicy:
    """Política de atenção — decide ACT/WAIT/IGNORE para cada evento."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def evaluate(self, event: AttentionEvaluation) -> AttentionDecision:
        """Avalia um evento e retorna a decisão de atenção.

        Lógica (extensível):
        1. Se ignorável → IGNORE
        2. Se urgente e relevance alta → ACT
        3. Se user não disponível → WAIT
        4. Se importance alta e internal state permite → ACT
        5. Caso contrário → WAIT
        """
        # Regra 1: eventos de baixa relevância são ignorados
        if event.relevance < 0.2:
            event.decision = AttentionDecision.IGNORE
            event.reasoning = f"Relevância baixa ({event.relevance:.2f})"
            self._log(event)
            return event.decision

        # Regra 2: urgência alta + relevância alta → ACT
        if event.urgency > 0.8 and event.relevance > 0.6:
            event.decision = AttentionDecision.ACT
            event.reasoning = f"Urgência ({event.urgency:.2f}) + relevância ({event.relevance:.2f})"
            self._log(event)
            return event.decision

        # Regra 3: usuário não disponível → WAIT
        if not event.user_available:
            event.decision = AttentionDecision.WAIT
            event.reasoning = "Usuário não disponível"
            self._log(event)
            return event.decision

        # Regra 4: alta importância + internal state positivo → ACT
        if event.importance > 0.7 and self._state_allows_action(event.internal_state):
            event.decision = AttentionDecision.ACT
            event.reasoning = f"Importância alta ({event.importance:.2f}) + estado interno favorável"
            self._log(event)
            return event.decision

        # Default: WAIT
        event.decision = AttentionDecision.WAIT
        event.reasoning = "Condições não suficientes para ação imediata"
        self._log(event)
        return event.decision

    def _state_allows_action(self, internal_state: dict[str, Any]) -> bool:
        """Verifica se o estado interno permite ação."""
        # Evitar ação quando Mia está sobrecarregada ou em estado muito negativo
        overload = internal_state.get("overloaded", False)
        extreme_negative = internal_state.get("mood_valence", 0.0) < -0.8
        return not overload and not extreme_negative

    def _log(self, evaluation: AttentionEvaluation) -> None:
        """Registra a decisão no attention_log."""
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            """INSERT INTO attention_log
               (id, event_type, event_id, decision, relevance, urgency,
                importance, reasoning, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                evaluation.event_type,
                evaluation.event_id,
                evaluation.decision.value,
                evaluation.relevance,
                evaluation.urgency,
                evaluation.importance,
                evaluation.reasoning,
                now,
            ),
        )
        self._db.commit()

    def recent_decisions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retorna decisões recentes de atenção."""
        return self._db.fetchall(
            "SELECT * FROM attention_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
