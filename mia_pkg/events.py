"""Event Bus in-process pub/sub síncrono.

Eventos tipados conforme contrato D.1 da especificação.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ======================================================================
# EventType enum — todos os tipos da especificação
# ======================================================================

class EventType(str, Enum):
    # Input
    MIGUEL_SPOKE = "miguel_spoke"
    MIGUEL_LEFT = "miguel_left"
    MIGUEL_RETURNED = "miguel_returned"
    INSULT_RECEIVED = "insult_received"
    COMPLIMENT_RECEIVED = "compliment_received"
    NEW_PERSON_DETECTED = "new_person_detected"
    CAMERA_ACTIVITY_DETECTED = "camera_activity_detected"
    # Voice (Fase 9)
    SPEECH_DETECTED = "speech_detected"
    SPEECH_TRANSCRIBED = "speech_transcribed"
    SPEAKER_IDENTIFIED = "speaker_identified"
    SPEECH_DIRECTED = "speech_directed"
    SPEECH_IGNORED = "speech_ignored"
    TTS_GENERATED = "tts_generated"
    # Perception (Fase 10)
    VISUAL_ANALYZED = "visual_analyzed"
    PERCEPTION_FUSED = "perception_fused"
    # Distributed (Fase 12)
    NODE_ONLINE = "node_online"
    NODE_OFFLINE = "node_offline"
    SYNC_COMPLETED = "sync_completed"
    # Task
    TASK_FAILED = "task_failed"
    TASK_COMPLETED = "task_completed"
    # Memory
    NEW_MEMORY_CANDIDATE = "new_memory_candidate"
    # Internal
    LONELINESS_CHANGED = "loneliness_changed"
    CURIOSITY_TRIGGERED = "curiosity_triggered"
    # Autonomous
    RESEARCH_COMPLETED = "research_completed"
    SELF_IMPROVEMENT_PROPOSED = "self_improvement_proposed"
    # Onboarding v2
    STATE_CHANGED = "state_changed"
    BELIEF_UPDATED = "belief_updated"
    NEED_FULFILLED = "need_fulfilled"
    DESIRE_FULFILLED = "desire_fulfilled"
    ATTENTION_DECISION = "attention_decision"


# ======================================================================
# Event dataclass
# ======================================================================

@dataclass
class Event:
    """Evento tipado conforme contrato D.1."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: EventType = EventType.MIGUEL_SPOKE
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""  # componente que emitiu
    schema_version: int = 1
    payload: dict[str, Any] = field(default_factory=dict)


# ======================================================================
# EventBus — pub/sub síncrono in-process
# ======================================================================

# Tipo do handler
Handler = Callable[[Event], None]


class EventBus:
    """Event Bus in-process pub/sub síncrono.

    - subscribe(event_type, handler) -> subscription_id
    - unsubscribe(subscription_id)
    - emit(event) — dispara síncronamente, rejeita inválido

    Segurança: circuit breaker após N erros consecutivos.
    """

    def __init__(self, circuit_breaker_threshold: int = 5) -> None:
        self._subscribers: dict[str, list[tuple[str, Handler]]] = {}
        self._handler_count: dict[str, int] = {}  # subscription_id -> counter
        self._next_id: int = 0
        self._circuit_breaker_threshold = circuit_breaker_threshold
        # producers isolados por circuit breaker
        self._error_counts: dict[str, int] = {}

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def subscribe(self, event_type: EventType | str, handler: Handler) -> str:
        """Registra um handler para um tipo de evento.

        Retorna subscription_id para unsubscribe posterior.
        """
        etype = event_type.value if isinstance(event_type, EventType) else event_type
        sub_id = f"sub_{self._next_id}"
        self._next_id += 1

        if etype not in self._subscribers:
            self._subscribers[etype] = []
        self._subscribers[etype].append((sub_id, handler))
        self._handler_count[sub_id] = 0

        logger.debug("Subscrito em %s: %s", etype, sub_id)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove uma subscription pelo ID."""
        for etype, handlers in self._subscribers.items():
            self._subscribers[etype] = [
                (sid, h) for sid, h in handlers if sid != subscription_id
            ]
            if subscription_id in self._handler_count:
                del self._handler_count[subscription_id]

    def emit(self, event: Event) -> None:
        """Dispara evento síncronamente.

        Valida schema mínimo (type obrigatório). Rejeita eventos inválidos.
        """
        if not isinstance(event.type, EventType):
            logger.warning("Evento rejeitado: type inválido: %s", event.type)
            return

        etype = event.type.value
        handlers = self._subscribers.get(etype, [])

        if not handlers:
            logger.debug("Nenhum subscriber para %s", etype)
            return

        # Verifica circuit breaker por source
        if self._error_counts.get(event.source, 0) >= self._circuit_breaker_threshold:
            logger.warning(
                "Circuit breaker ativo para '%s' — evento ignorado.", event.source
            )
            return

        for sub_id, handler in handlers:
            try:
                handler(event)
                self._handler_count[sub_id] = self._handler_count.get(sub_id, 0) + 1
            except Exception:
                self._error_counts[event.source] = (
                    self._error_counts.get(event.source, 0) + 1
                )
                logger.exception(
                    "Erro ao entregar evento %s para handler %s", etype, sub_id
                )

    def subscriber_count(self, event_type: EventType | str) -> int:
        """Retorna quantos subscribers existem para um tipo."""
        etype = event_type.value if isinstance(event_type, EventType) else event_type
        return len(self._subscribers.get(etype, []))
