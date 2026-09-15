"""Avatar / Embodiment — renderização visual + expressões emocionais.

Fase 11 do roadmap:
- Avatar Renderer: personagem visual com expressões (SVG puro, sem deps)
- Expression Mapper: EmotionState → config facial (olhos, boca, sobrancelhas)
- Avatar Sync: quando emoção muda, expressão atualiza (via EventBus)
- Avatar API: interface programática para sistemas externos

SVG escolhido: leve, sem dependências, renderiza em browser/obsidian/apps.
Estilo cartoon (R11.1: evitar uncanny valley).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus
from mia_pkg.affective_engine import AffectiveEngine, EmotionVector, MoodState

logger = logging.getLogger(__name__)


# ======================================================================
# Expressões
# ======================================================================

class Expression(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    LOVING = "loving"
    CURIOUS = "curious"
    BORED = "bored"


@dataclass
class FacialConfig:
    """Parâmetros da face cartoon."""
    expression: Expression = Expression.NEUTRAL
    # olhos
    eye_openness: float = 1.0       # 0 (fechado) a 1 (aberto)
    pupil_size: float = 0.5         # 0.2 a 1.0 (dilatação)
    brow_angle: float = 0.0         # -1 (raiva) a 1 (tristeza/surpresa)
    # boca
    mouth_curve: float = 0.0        # -1 (frown) a 1 (smile)
    mouth_openness: float = 0.0     # 0 (fechado) a 1 (aberto)
    # cor
    blush: float = 0.0              # 0 a 1 (vermelhidão)
    brightness: float = 1.0         # 0.5 a 1.2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExpressionMapper:
    """Mapeia EmotionState → FacialConfig."""

    # emoção → ajustes
    MAP: dict[Expression, dict[str, float]] = {
        Expression.NEUTRAL: {"eye_openness": 0.9, "pupil_size": 0.5, "brow_angle": 0.0,
                             "mouth_curve": 0.0, "mouth_openness": 0.0, "blush": 0.0},
        Expression.HAPPY: {"eye_openness": 0.85, "pupil_size": 0.6, "brow_angle": 0.3,
                           "mouth_curve": 0.8, "mouth_openness": 0.2, "blush": 0.4},
        Expression.SAD: {"eye_openness": 0.5, "pupil_size": 0.4, "brow_angle": 0.7,
                         "mouth_curve": -0.7, "mouth_openness": 0.0, "blush": 0.0,
                         "brightness": 0.85},
        Expression.ANGRY: {"eye_openness": 0.7, "pupil_size": 0.35, "brow_angle": -0.9,
                           "mouth_curve": -0.4, "mouth_openness": 0.3, "blush": 0.6,
                           "brightness": 1.05},
        Expression.FEARFUL: {"eye_openness": 1.0, "pupil_size": 0.8, "brow_angle": 0.8,
                             "mouth_curve": -0.3, "mouth_openness": 0.4, "blush": 0.1},
        Expression.SURPRISED: {"eye_openness": 1.0, "pupil_size": 0.9, "brow_angle": 1.0,
                               "mouth_curve": 0.1, "mouth_openness": 0.9, "blush": 0.1},
        Expression.DISGUSTED: {"eye_openness": 0.5, "pupil_size": 0.3, "brow_angle": -0.4,
                               "mouth_curve": -0.5, "mouth_openness": 0.1, "blush": 0.0},
        Expression.LOVING: {"eye_openness": 0.8, "pupil_size": 0.75, "brow_angle": 0.2,
                            "mouth_curve": 0.75, "mouth_openness": 0.1, "blush": 0.8},
        Expression.CURIOUS: {"eye_openness": 0.95, "pupil_size": 0.75, "brow_angle": 0.5,
                             "mouth_curve": 0.3, "mouth_openness": 0.15, "blush": 0.0},
        Expression.BORED: {"eye_openness": 0.4, "pupil_size": 0.4, "brow_angle": 0.1,
                           "mouth_curve": -0.2, "mouth_openness": 0.0, "blush": 0.0,
                           "brightness": 0.9},
    }

    def map_emotion(self, emotions: EmotionVector | None = None,
                    mood: MoodState | None = None) -> FacialConfig:
        """Converte estado emocional em parâmetros faciais.

        Prioridade: emoção dominante do EmotionVector; se empatado,
        usa valence/arousal do mood para escolher.
        """
        if emotions is None:
            emotions = EmotionVector()

        # emoção dominante
        dominant = self._dominant_emotion(emotions)
        config = FacialConfig(expression=dominant)
        base = self.MAP[dominant]
        for k, v in base.items():
            setattr(config, k, v)

        # ajusta intensidade pela magnitude da emoção
        intensity = max(
            emotions.happiness, emotions.sadness, emotions.anger,
            emotions.fear, emotions.surprise, emotions.disgust,
            emotions.affection, emotions.boredom,
        )
        config.mouth_curve *= intensity
        config.mouth_openness *= intensity
        config.blush *= intensity

        # ajustes pelo mood (suavização temporal)
        if mood is not None:
            if mood.valence < -0.3:
                config.mouth_curve = min(-0.2, config.mouth_curve - 0.3)
                config.brightness = max(0.7, config.brightness - 0.1)
            elif mood.valence > 0.5:
                config.mouth_curve = max(0.3, config.mouth_curve + 0.2)
            if mood.arousal > 0.8:
                config.pupil_size = min(1.0, config.pupil_size + 0.2)
                config.eye_openness = min(1.0, config.eye_openness + 0.1)

        return config

    @staticmethod
    def _dominant_emotion(emotions: EmotionVector) -> Expression:
        """Escolhe a expressão dominante pelo vetor emocional.

        Usa desvio acima do baseline: traços default 0.5 (trust, curiosity,
        affection) NÃO contam como expressão ativa — só emoções que se
        destacam do neutro.
        """
        # emocionais (baseline 0.5 no EmotionVector default — exigem desvio)
        emotive = [
            (emotions.happiness, Expression.HAPPY, 0.55),
            (emotions.sadness, Expression.SAD, 0.45),
            (emotions.anger, Expression.ANGRY, 0.45),
            (emotions.fear, Expression.FEARFUL, 0.45),
            (emotions.surprise, Expression.SURPRISED, 0.45),
            (emotions.disgust, Expression.DISGUSTED, 0.45),
        ]
        # relação/estado (baseline 0.5 — precisam desviar mais)
        relational = [
            (emotions.affection, Expression.LOVING, 0.7),
            (emotions.curiosity_level, Expression.CURIOUS, 0.7),
            (emotions.boredom, Expression.BORED, 0.6),
        ]
        candidates = emotive + relational
        # filtra acima do threshold individual
        active = [(val, expr) for val, expr, thr in candidates if val >= thr]
        if not active:
            return Expression.NEUTRAL
        # dominante = maior intensidade entre as ativas
        best = max(active, key=lambda c: c[0])
        return best[1]


# ======================================================================
# Avatar Renderer (SVG)
# ======================================================================

class AvatarRenderer:
    """Renderiza avatar como SVG (estilo cartoon)."""

    # paleta
    SKIN = "#f5c9a6"
    SKIN_SHADOW = "#e0a98a"
    HAIR = "#4a2c17"
    OUTLINE = "#2d1b0e"

    def __init__(self, style: str = "cartoon", size: int = 200) -> None:
        self._style = style
        self._size = size

    def render(self, config: FacialConfig) -> str:
        """Gera SVG da face conforme config."""
        s = self._size
        cx, cy = s / 2, s / 2
        r_face = s * 0.32

        eye_y = cy - s * 0.05
        eye_dx = s * 0.12
        eye_open = max(0.08, config.eye_openness * s * 0.07)
        pupil_r = config.pupil_size * s * 0.028
        brow_y = eye_y - s * 0.11
        brow_h = s * 0.05
        brow_tilt = config.brow_angle * s * 0.06

        mouth_y = cy + s * 0.14
        mouth_open = config.mouth_openness * s * 0.09
        mouth_curve = config.mouth_curve * s * 0.06

        # cor da pele com blush
        skin = self.SKIN
        blush_alpha = config.blush

        # sobrancelhas (esquerda/direita com inclinação)
        left_brow = (
            f'<path d="M {cx - eye_dx - s*0.06} {brow_y - brow_tilt} '
            f'Q {cx - eye_dx} {brow_y - brow_h - brow_tilt} '
            f'{cx - eye_dx + s*0.06} {brow_y - brow_tilt}" '
            f'stroke="{self.OUTLINE}" stroke-width="{s*0.012}" fill="none"/>'
        )
        right_brow = (
            f'<path d="M {cx + eye_dx - s*0.06} {brow_y + brow_tilt} '
            f'Q {cx + eye_dx} {brow_y - brow_h + brow_tilt} '
            f'{cx + eye_dx + s*0.06} {brow_y + brow_tilt}" '
            f'stroke="{self.OUTLINE}" stroke-width="{s*0.012}" fill="none"/>'
        )

        # olhos (elipses com brilho)
        def eye(ex):
            return (
                f'<ellipse cx="{ex}" cy="{eye_y}" rx="{s*0.05}" ry="{max(0.02, eye_open)}" '
                f'fill="white" stroke="{self.OUTLINE}" stroke-width="{s*0.008}"/>'
                f'<circle cx="{ex}" cy="{eye_y}" r="{pupil_r}" fill="{self.OUTLINE}"/>'
                f'<circle cx="{ex - pupil_r*0.3}" cy="{eye_y - pupil_r*0.3}" r="{pupil_r*0.3}" fill="white"/>'
            )
        eyes = eye(cx - eye_dx) + eye(cx + eye_dx)

        # boca
        if mouth_open > 0.02:
            mouth = (
                f'<ellipse cx="{cx}" cy="{mouth_y}" rx="{s*0.06}" ry="{mouth_open}" '
                f'fill="#7a3b2e" stroke="{self.OUTLINE}" stroke-width="{s*0.008}"/>'
            )
        else:
            mouth = (
                f'<path d="M {cx - s*0.06} {mouth_y} Q {cx} {mouth_y - mouth_curve} '
                f'{cx + s*0.06} {mouth_y}" '
                f'stroke="{self.OUTLINE}" stroke-width="{s*0.012}" fill="none"/>'
            )

        # blush
        blushes = ""
        if blush_alpha > 0.05:
            blushes = (
                f'<ellipse cx="{cx - eye_dx - s*0.03}" cy="{cy + s*0.08}" rx="{s*0.05}" '
                f'ry="{s*0.03}" fill="#e88a8a" opacity="{min(1, blush_alpha)}"/>'
                f'<ellipse cx="{cx + eye_dx + s*0.03}" cy="{cy + s*0.08}" rx="{s*0.05}" '
                f'ry="{s*0.03}" fill="#e88a8a" opacity="{min(1, blush_alpha)}"/>'
            )

        # cabelo (topo)
        hair = (
            f'<path d="M {cx - r_face*0.95} {cy - r_face*0.2} '
            f'Q {cx - r_face*0.8} {cy - r_face*1.1} {cx} {cy - r_face*1.05} '
            f'Q {cx + r_face*0.8} {cy - r_face*1.1} {cx + r_face*0.95} {cy - r_face*0.2} '
            f'Q {cx + r_face*0.7} {cy - r_face*0.4} {cx} {cy - r_face*0.45} '
            f'Q {cx - r_face*0.7} {cy - r_face*0.4} {cx - r_face*0.95} {cy - r_face*0.2} Z" '
            f'fill="{self.HAIR}" stroke="{self.OUTLINE}" stroke-width="{s*0.01}"/>'
        )

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" '
            f'viewBox="0 0 {s} {s}">'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r_face}" ry="{r_face*1.05}" '
            f'fill="{skin}" stroke="{self.OUTLINE}" stroke-width="{s*0.012}"/>'
            f'{hair}'
            f'{eyes}'
            f'{left_brow}{right_brow}'
            f'{blushes}'
            f'{mouth}'
            f'</svg>'
        )
        return svg

    def render_to_file(self, config: FacialConfig, path: str) -> str:
        svg = self.render(config)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        return path


# ======================================================================
# Avatar Sync — reage a mudanças emocionais
# ======================================================================

class AvatarSync:
    """Escuta EmotionState changes e atualiza a expressão.

    Responsivo: processa mudanças imediatamente (subscrição síncrona).
    """

    def __init__(
        self,
        db: SQLiteConnection,
        renderer: AvatarRenderer,
        bus: EventBus | None = None,
        on_update: Callable[[FacialConfig], None] | None = None,
    ) -> None:
        self._db = db
        self._engine = AffectiveEngine(db)
        self._renderer = renderer
        self._mapper = ExpressionMapper()
        self._bus = bus or EventBus()
        self._on_update = on_update
        self._current: FacialConfig = FacialConfig()
        self._last_update_s = time.time()

        # escuta mudanças de estado (STATE_CHANGED de emotion_state)
        self._bus.subscribe(EventType.STATE_CHANGED, self._on_state_changed)

    def _on_state_changed(self, event: Event) -> None:
        payload = event.payload or {}
        if payload.get("target") == "emotion":
            self.update()

    def update(self) -> FacialConfig:
        """Re-lê estado emocional e atualiza expressão."""
        state = self._engine.get_current()
        emotions = state.emotions
        mood = state.mood
        config = self._mapper.map_emotion(emotions, mood)
        self._current = config
        self._last_update_s = time.time()
        if self._on_update:
            self._on_update(config)
        return config

    @property
    def current_expression(self) -> Expression:
        return self._current.expression

    @property
    def last_update_s(self) -> float:
        return self._last_update_s


# ======================================================================
# Avatar API
# ======================================================================

class AvatarAPI:
    """Interface programática para sistemas externos."""

    def __init__(self, sync: AvatarSync, renderer: AvatarRenderer) -> None:
        self._sync = sync
        self._renderer = renderer

    def current_expression(self) -> dict[str, Any]:
        return self._sync._current.to_dict()

    def current_svg(self, size: int | None = None) -> str:
        return self._renderer.render(self._sync._current)

    def save_snapshot(self, path: str) -> str:
        return self._renderer.render_to_file(self._sync._current, path)