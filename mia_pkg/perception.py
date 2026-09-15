"""Vision / Perception Pipeline — câmera → análise → eventos → contexto.

Fase 10 do roadmap:
- Vision Pipeline: captura frames → análise por LLM de visão (plugável)
- Perception Aggregator: combina visão + áudio + outros sensores
- Eventos: CAMERA_ACTIVITY_DETECTED, NEW_PERSON_DETECTED
- Context Enricher: percepção enriquece contexto para Cognitive Core
- Privacy: rostos/terceiros processados localmente (nunca upload)
- Rate limiting: análise visual não excede budget

Tudo plugável (analyze_fn): em produção aponta para modelo multimodal
local (LLaVA, llama.cpp) ou de confiança; em testes usa mock.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus

logger = logging.getLogger(__name__)


# ======================================================================
# Tipos
# ======================================================================

@dataclass
class VisionFrame:
    """Um frame capturado."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    width: int = 640
    height: int = 480
    timestamp: float = field(default_factory=time.time)
    pixels: bytes = b""  # dados opcionais (nunca enviados p/ nuvem sem opt-in)
    source: str = "camera"


@dataclass
class VisualObservation:
    """Resultado da análise de um frame."""
    frame_id: str
    activity: str  # "none", "person", "movement", "object", ...
    description: str
    people_visible: int = 0
    objects: list[str] = field(default_factory=list)
    emotion_visible: str = "neutral"
    confidence: float = 0.0


@dataclass
class PerceptionEvent:
    """Evento de percepção consolidado (agregador)."""
    sensor: str  # "vision", "audio", "proximity", ...
    kind: str    # "person", "movement", "activity", ...
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.3


# ======================================================================
# Vision Pipeline
# ======================================================================

class VisionPipeline:
    """Captura frames → analisa → emite eventos.

    `analyze_fn(frame) → VisualObservation` plugável. Padrão: mock que
    retorna "none" (sem atividade) para não custar nada.
    """

    def __init__(
        self,
        analyze_fn: Callable[[VisionFrame], VisualObservation] | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._fn = analyze_fn or self._default_analyze
        self._bus = bus or EventBus()
        self._last_obs: VisualObservation | None = None

    @staticmethod
    def _default_analyze(frame: VisionFrame) -> VisualObservation:
        return VisualObservation(
            frame_id=frame.id,
            activity="none",
            description="[análise visual não configurada]",
            confidence=0.0,
        )

    def analyze(self, frame: VisionFrame) -> VisualObservation:
        """Analisa frame, emite CAMERA_ACTIVITY_DETECTED, retorna observação."""
        obs = self._fn(frame)
        self._last_obs = obs

        # evento apenas se há atividade
        if obs.activity != "none" and obs.confidence > 0.3:
            self._bus.emit(Event(
                type=EventType.CAMERA_ACTIVITY_DETECTED,
                payload={
                    "activity": obs.activity,
                    "description": obs.description,
                    "people": obs.people_visible,
                    "confidence": obs.confidence,
                },
                source="vision",
            ))

        # NEW_PERSON_DETECTED
        if obs.people_visible > 0 and obs.activity == "person":
            self._bus.emit(Event(
                type=EventType.NEW_PERSON_DETECTED,
                payload={"count": obs.people_visible, "description": obs.description},
                source="vision",
            ))
        return obs

    @property
    def last_observation(self) -> VisualObservation | None:
        return self._last_obs


# ======================================================================
# Rate Limiter visual
# ======================================================================

class VisionRateLimiter:
    """Limita análises visuais por janela (budget)."""

    def __init__(self, max_per_minute: int = 6, window_s: float = 60.0) -> None:
        self._max = max_per_minute
        self._window = window_s
        self._calls: list[float] = []

    def allow(self) -> bool:
        now = time.time()
        self._calls = [t for t in self._calls if now - t < self._window]
        if len(self._calls) >= self._max:
            return False
        self._calls.append(now)
        return True

    def remaining(self) -> int:
        now = time.time()
        self._calls = [t for t in self._calls if now - t < self._window]
        return max(0, self._max - len(self._calls))


# ======================================================================
# Perception Aggregator
# ======================================================================

class PerceptionAggregator:
    """Combina percepções de múltiplos sensores em eventos consolidados.

    Regras:
    - Visão (pessoa) + áudio (fala) → "person_interacting" (alta importancia)
    - Visão (movimento) → "activity" (média)
    - Áudio (fala sem visão) → "voice_activity" (baixa)
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or EventBus()
        self._recent: list[PerceptionEvent] = []
        self._window_s = 5.0

    def add(self, event: PerceptionEvent) -> PerceptionEvent:
        """Registra percepção e tenta fusão."""
        self._recent = [e for e in self._recent if time.time() - e.timestamp < self._window_s]
        self._recent.append(event)

        fused = self._try_fuse(event)
        return fused or event

    def _try_fuse(self, event: PerceptionEvent) -> PerceptionEvent | None:
        """Tenta combinar com percepções recentes de outros sensores."""
        now = time.time()
        for other in self._recent:
            if other is event:
                continue
            # visão (pessoa) + áudio (fala) → person_interacting
            # (qualquer ordem: vision+audio OU audio+vision)
            vision = event if event.sensor == "vision" else other
            audio = event if event.sensor == "audio" else other
            if (
                event.sensor in ("vision", "audio")
                and other.sensor in ("vision", "audio")
                and event.sensor != other.sensor
                and vision.kind == "person"
                and audio.kind == "speech"
            ):
                fused = PerceptionEvent(
                    sensor="fusion",
                    kind="person_interacting",
                    payload={"vision": vision.payload, "audio": audio.payload},
                    timestamp=now,
                    importance=0.8,
                )
                self._bus.emit(Event(
                    type=EventType.PERCEPTION_FUSED,
                    payload={"fusion": "person_interacting", "importance": 0.8},
                    source="perception_aggregator",
                ))
                return fused
        return None

    def current_picture(self) -> dict[str, list[PerceptionEvent]]:
        """Snapshot das percepções recentes por sensor."""
        self._recent = [e for e in self._recent if time.time() - e.timestamp < self._window_s]
        picture: dict[str, list[PerceptionEvent]] = {}
        for e in self._recent:
            picture.setdefault(e.sensor, []).append(e)
        return picture


# ======================================================================
# Context Enricher
# ======================================================================

class ContextEnricher:
    """Adiciona percepção ao contexto do Cognitive Core.

    Gera um bloco de texto estruturado que é injetado no system prompt
    (via ContextAssembler) ou nos inputs.
    """

    def __init__(self, aggregator: PerceptionAggregator) -> None:
        self._agg = aggregator

    def enrich(self, base_context: str = "") -> str:
        """Retorna o contexto base + bloco de percepção atual."""
        picture = self._agg.current_picture()
        if not picture:
            return base_context

        lines = ["Percepção atual:"]
        for sensor, events in picture.items():
            for e in events:
                lines.append(f"- {sensor}/{e.kind}: {e.payload}")
        perception_block = "\n".join(lines)
        if base_context:
            return base_context + "\n\n" + perception_block
        return perception_block

    def has_perception(self) -> bool:
        return bool(self._agg.current_picture())