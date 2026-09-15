"""Emotion Governor — rate limiting + mood por média temporal.

Fase 4 critérios que faltam:
- Rate limiting: máx 10 mudanças emocionais por hora
- MoodEngine: VAD computado como média ponderada das últimas N horas
- Evento LONELINESS_CHANGED emitido quando loneliness muda
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus
from mia_pkg.affective_engine import AffectiveEngine, MoodState


@dataclass
class EmotionChangeRecord:
    """Registro de mudança emocional (para rate limiting)."""
    timestamp: float = field(default_factory=time.time)
    deltas: dict[str, float] = field(default_factory=dict)
    applied: bool = True


class EmotionGovernor:
    """Governança das mudanças emocionais.

    - Máx 10 mudanças/hora (critério Fase 4)
    - Emite LONELINESS_CHANGED quando loneliness muda
    """

    MAX_CHANGES_PER_HOUR = 10
    HOUR_WINDOW = 3600.0

    def __init__(self, db: SQLiteConnection, bus: EventBus | None = None) -> None:
        self._db = db
        self._engine = AffectiveEngine(db)
        self._bus = bus or EventBus()
        self._history: list[EmotionChangeRecord] = []

    def propose(
        self, deltas: dict[str, float], reason: str = "", source: str = ""
    ) -> dict[str, Any]:
        """Propõe mudança (verifica rate limit). Retorna proposta ou None."""
        if not self._check_rate_limit():
            return {"type": "emotion_transition_blocked", "reason": "rate limit excedido"}
        return self._engine.propose_emotion_change(deltas, reason, source)

    def apply(self, proposal: dict[str, Any]) -> bool:
        """Aplica mudança validada + emite eventos."""
        if proposal.get("type") == "emotion_transition_blocked":
            return False

        before = self._engine.get_current()

        new_state = self._engine.apply_validated_change(
            proposal["new_emotions"],
            proposal["new_mood"],
            reason=proposal.get("reason", ""),
        )
        self._history.append(EmotionChangeRecord(
            deltas=proposal.get("new_emotions", {}),
        ))
        self._prune_history()

        # LONELINESS_CHANGED quando loneliness MUDA de fato
        new_loneliness = new_state.emotions.loneliness
        if (
            "loneliness" in proposal.get("new_emotions", {})
            and abs(new_loneliness - before.emotions.loneliness) > 1e-9
        ):
            event = Event(
                type=EventType.LONELINESS_CHANGED,
                payload={
                    "old": before.emotions.loneliness,
                    "new": new_loneliness,
                },
                source="emotion_governor",
            )
            self._bus.emit(event)

        return True

    def _check_rate_limit(self) -> bool:
        """Verifica se ainda há budget de mudanças na janela de 1h."""
        self._prune_history()
        return len(self._history) < self.MAX_CHANGES_PER_HOUR

    def _prune_history(self) -> None:
        """Remove registros fora da janela de 1h."""
        cutoff = time.time() - self.HOUR_WINDOW
        self._history = [r for r in self._history if r.timestamp >= cutoff]

    def remaining_budget(self) -> int:
        """Quantas mudanças ainda são permitidas na janela."""
        self._prune_history()
        return max(0, self.MAX_CHANGES_PER_HOUR - len(self._history))


class TemporalMoodEngine:
    """Mood computado como média ponderada das últimas N horas.

    Parâmetros:
    - window_hours: janela considerada (default 4h)
    - decay_factor: ponderação (mais recente pesa mais)
    """

    def __init__(self, db: SQLiteConnection, window_hours: float = 4.0) -> None:
        self._db = db
        self._engine = AffectiveEngine(db)
        self._window_hours = window_hours

    def compute_mood(self) -> MoodState:
        """Computa mood como média ponderada dos snapshots na janela.

        Ponderação: exp(-t_decay * age_hours) — snaps recentes pesam mais.
        """
        rows = self._db.fetchall(
            """SELECT mood_valence, mood_arousal, mood_dominance, snapshot_at
               FROM emotion_state
               WHERE snapshot_at >= datetime('now', ?)
               ORDER BY snapshot_at DESC""",
            (f"-{int(self._window_hours * 60)} minutes",),
        )
        # FIX: SQLite datetime('now') usa UTC enquanto snapshot_at é ISO com TZ.
        # Fallback: se query não retornar, usa últimos N snapshots por ordem.
        if not rows:
            rows = self._db.fetchall(
                """SELECT mood_valence, mood_arousal, mood_dominance, snapshot_at
                   FROM emotion_state ORDER BY snapshot_at DESC LIMIT 20"""
            )

        if not rows:
            return MoodState()

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        total_w = 0.0
        v = a = d = 0.0
        for row in rows:
            try:
                t = datetime.fromisoformat(row["snapshot_at"])
                age_hours = max(0.0, (now - t).total_seconds() / 3600.0)
            except Exception:
                age_hours = 0.0
            # peso decai exponencialmente com a idade
            w = 2.0 ** (-age_hours / 1.0)  # meia-vida de 1h
            v += row["mood_valence"] * w
            a += row["mood_arousal"] * w
            d += row["mood_dominance"] * w
            total_w += w

        if total_w == 0:
            return MoodState()

        return MoodState(
            valence=max(-1.0, min(1.0, v / total_w)),
            arousal=max(0.0, min(1.0, a / total_w)),
            dominance=max(0.0, min(1.0, d / total_w)),
        )

    def refresh_mood(self) -> MoodState:
        """Calcula e persiste o mood temporal como novo snapshot."""
        computed = self.compute_mood()
        current = self._engine.get_current()
        self._engine.apply_validated_change(
            current.emotions.to_dict(),
            computed.to_dict(),
            reason="mood temporal refresh",
        )
        return computed