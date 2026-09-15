"""Affective Engine — implementação de D.6 (Emotion State Schema).

Gerencia emoções (vetorial), mood (suavização temporal) e sensações.

O LLM NÃO escreve aqui diretamente. O Cognitive Core propõe mudanças via State Authority.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType


# ======================================================================
# Dataclasses — conforme spec D.6
# ======================================================================

@dataclass
class EmotionVector:
    """Vetor de emoções normalizado (0.0–1.0)."""
    happiness: float = 0.5
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    trust_level: float = 0.5
    anticipation: float = 0.5
    # Derivados
    curiosity_level: float = 0.5
    loneliness: float = 0.0
    affection: float = 0.5
    boredom: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> EmotionVector:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class MoodState:
    """Mood como suavização temporal do emotion vector.

    - valence: -1.0 (negativo) a 1.0 (positivo)
    - arousal: 0.0 (calmo) a 1.0 (excitado)
    - dominance: 0.0 (submisso) a 1.0 (dominante)
    """
    valence: float = 0.0
    arousal: float = 0.5
    dominance: float = 0.5

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> MoodState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Sensation:
    """Sensação interna abstrata — pode existir sem causa conhecida (§16)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pleasantness: float = 0.5    # -1.0 (desagradável) a 1.0 (agradável)
    arousal: float = 0.5         # 0.0 (calmo) a 1.0 (excitado)
    intensity: float = 0.5       # 0.0 a 1.0
    cause_known: bool = False
    cause_description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmotionState:
    """Snapshot completo do estado emocional (D.6)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    emotions: EmotionVector = field(default_factory=EmotionVector)
    mood: MoodState = field(default_factory=MoodState)
    sensations: list[Sensation] = field(default_factory=list)
    snapshot_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ======================================================================
# Affective Engine
# ======================================================================

class AffectiveEngine:
    """Gerencia estado emocional persistente.

    Componentes:
    - EmotionEngine: transições de emoção
    - MoodEngine: suavização temporal do mood
    - SensationManager: sensações sem causa consciente
    """

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def get_current(self) -> EmotionState:
        """Retorna o estado emocional mais recente."""
        row = self._db.fetchone(
            "SELECT * FROM emotion_state ORDER BY snapshot_at DESC LIMIT 1"
        )
        if not row:
            # Estado inicial
            state = EmotionState()
            self._save(state)
            return state
        return self._row_to_state(row)

    # ------------------------------------------------------------------
    # Transições de emoção (propostas — passam pela State Authority)
    # ------------------------------------------------------------------

    def propose_emotion_change(
        self,
        deltas: dict[str, float],
        reason: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Propõe mudanças no emotion vector.

        Retorna a proposta como dict para ser processada pela State Authority.
        NÃO aplica diretamente — a State Authority decide.
        """
        current = self.get_current()
        new_emotions = EmotionVector(**current.emotions.to_dict())

        # Aplica deltas (clamped 0-1)
        for key, delta in deltas.items():
            if hasattr(new_emotions, key):
                old = getattr(new_emotions, key)
                new_val = max(0.0, min(1.0, old + delta))
                setattr(new_emotions, key, new_val)

        # Mood derivation do emotion vector
        new_mood = self._derive_mood(new_emotions)

        return {
            "type": "emotion_transition",
            "current_snapshot_id": current.id,
            "new_emotions": new_emotions.to_dict(),
            "new_mood": new_mood.to_dict(),
            "reason": reason,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def apply_validated_change(
        self,
        new_emotions_dict: dict[str, float],
        new_mood_dict: dict[str, float],
        reason: str = "",
    ) -> EmotionState:
        """Aplica uma mudança VALIDADA pela State Authority."""
        emotions = EmotionVector.from_dict(new_emotions_dict)
        mood = MoodState.from_dict(new_mood_dict)
        current = self.get_current()

        new_state = EmotionState(
            id=str(uuid.uuid4()),
            emotions=emotions,
            mood=mood,
            sensations=current.sensations,
        )
        self._save(new_state)
        return new_state

    # ------------------------------------------------------------------
    # Sensações
    # ------------------------------------------------------------------

    def add_sensation(
        self,
        pleasantness: float,
        arousal: float,
        intensity: float,
        cause_known: bool = False,
        cause_description: str = "",
    ) -> Sensation:
        """Registra uma sensação (pode existir sem causa conhecida)."""
        sensation = Sensation(
            pleasantness=pleasantness,
            arousal=arousal,
            intensity=intensity,
            cause_known=cause_known,
            cause_description=cause_description,
        )
        current = self.get_current()
        current.sensations.append(sensation)

        # Persiste sensação na tabela sensations
        self._db.execute(
            """INSERT INTO sensations
               (id, pleasantness, arousal, intensity, cause_known,
                cause_description, created_at, emotion_state_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sensation.id, sensation.pleasantness, sensation.arousal,
                sensation.intensity, 1 if sensation.cause_known else 0,
                sensation.cause_description, sensation.created_at,
                current.id,
            ),
        )
        self._db.commit()
        return sensation

    def get_recent_sensations(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retorna sensações recentes."""
        return self._db.fetchall(
            "SELECT * FROM sensations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )

    # ------------------------------------------------------------------
    # Mood suavização temporal
    # ------------------------------------------------------------------

    def smooth_mood(self, decay: float = 0.05) -> MoodState:
        """Aplica suavização temporal no mood (converge para neutro).

        Deve ser chamado periodicamente (ex: a cada 5 minutos).
        O decay controla a velocidade de convergência.
        """
        current = self.get_current()
        mood = current.mood

        # Suavização: move mood em direção ao neutro
        new_valence = mood.valence * (1.0 - decay)
        new_arousal = mood.arousal * (1.0 - decay) + 0.5 * decay
        new_dominance = mood.dominance * (1.0 - decay) + 0.5 * decay

        new_mood = MoodState(
            valence=max(-1.0, min(1.0, new_valence)),
            arousal=max(0.0, min(1.0, new_arousal)),
            dominance=max(0.0, min(1.0, new_dominance)),
        )

        # Aplica diretamente (suavização é operação interna, não precisa de LLM)
        new_state = EmotionState(
            emotions=current.emotions,
            mood=new_mood,
            sensations=current.sensations,
        )
        self._save(new_state)
        return new_mood

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _derive_mood(self, emotions: EmotionVector) -> MoodState:
        """Deriva mood do emotion vector (conforme spec D.6)."""
        # Valence: positivo (happiness, affection) vs negativo (sadness, anger, fear)
        positive = (emotions.happiness + emotions.affection + emotions.anticipation) / 3.0
        negative = (emotions.sadness + emotions.anger + emotions.fear + emotions.disgust) / 4.0
        valence = (positive - negative)  # range: -1 a 1

        # Arousal: alta com excitement (surprise, anger, fear), baixa com calm
        arousal = (emotions.surprise + emotions.anger + emotions.fear +
                   emotions.anticipation + emotions.curiosity_level) / 5.0

        # Dominance: alta com confidence/trust, baixa com fear/sadness
        dominance = (emotions.trust_level + emotions.happiness -
                     emotions.fear - emotions.sadness + 1.0) / 4.0

        return MoodState(
            valence=max(-1.0, min(1.0, valence)),
            arousal=max(0.0, min(1.0, arousal)),
            dominance=max(0.0, min(1.0, dominance)),
        )

    def _save(self, state: EmotionState) -> None:
        """Persiste estado emocional."""
        self._db.execute(
            """INSERT INTO emotion_state
               (id, happiness, sadness, anger, fear, surprise, disgust,
                trust_level, anticipation, curiosity_level, loneliness,
                affection, boredom, mood_valence, mood_arousal,
                mood_dominance, snapshot_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.id,
                state.emotions.happiness, state.emotions.sadness,
                state.emotions.anger, state.emotions.fear,
                state.emotions.surprise, state.emotions.disgust,
                state.emotions.trust_level, state.emotions.anticipation,
                state.emotions.curiosity_level, state.emotions.loneliness,
                state.emotions.affection, state.emotions.boredom,
                state.mood.valence, state.mood.arousal, state.mood.dominance,
                state.snapshot_at,
            ),
        )
        self._db.commit()

    def _row_to_state(self, row: dict[str, Any]) -> EmotionState:
        """Converte row do banco para EmotionState."""
        emotions = EmotionVector(
            happiness=row["happiness"],
            sadness=row["sadness"],
            anger=row["anger"],
            fear=row["fear"],
            surprise=row["surprise"],
            disgust=row["disgust"],
            trust_level=row["trust_level"],
            anticipation=row["anticipation"],
            curiosity_level=row["curiosity_level"],
            loneliness=row["loneliness"],
            affection=row["affection"],
            boredom=row["boredom"],
        )
        mood = MoodState(
            valence=row["mood_valence"],
            arousal=row["mood_arousal"],
            dominance=row["mood_dominance"],
        )
        # Sensações da tabela sensations
        sensation_rows = self._db.fetchall(
            "SELECT * FROM sensations WHERE emotion_state_id=? ORDER BY created_at",
            (row["id"],),
        )
        sensations = [
            Sensation(
                id=s["id"], pleasantness=s["pleasantness"], arousal=s["arousal"],
                intensity=s["intensity"], cause_known=bool(s["cause_known"]),
                cause_description=s.get("cause_description", ""),
                created_at=s["created_at"],
            )
            for s in sensation_rows
        ]
        return EmotionState(
            id=row["id"],
            emotions=emotions,
            mood=mood,
            sensations=sensations,
            snapshot_at=row["snapshot_at"],
        )
