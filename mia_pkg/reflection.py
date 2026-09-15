"""Reflection — Diary Store, Reflection Engine, Imagination Engine.

Fase 7 do roadmap: Mia reflete sobre si mesma e o mundo.
Diário subjetivo (append-only), reflexões a partir de estado real,
imaginação controlada de cenários hipotéticos.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus


# ======================================================================
# Dataclasses
# ======================================================================

class EntryType(str, Enum):
    MOMENT = "moment"          # registro pontual
    SUMMARY = "summary"        # resumo diário
    REFLECTION = "reflection"  # reflexão sobre si/mundo


@dataclass
class DiaryEntry:
    """Uma entrada do diário (append-only)."""
    content: str
    date: str = field(default_factory=lambda: date.today().isoformat())
    entry_type: EntryType = EntryType.MOMENT
    emotion_snapshot: dict[str, Any] | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def word_count(self) -> int:
        return len(self.content.split())


@dataclass
class Reflection:
    """Uma reflexão gerada a partir de estado + memórias."""
    content: str
    triggered_by: str = "manual"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sources: list[str] = field(default_factory=list)  # memórias/estado usados


@dataclass
class ImaginationScenario:
    """Um cenário hipotético simulado."""
    prompt: str
    result: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ======================================================================
# Diary Store
# ======================================================================

class DiaryStore:
    """Diário append-only em SQLite."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def append(self, entry: DiaryEntry) -> DiaryEntry:
        self._db.execute(
            """INSERT INTO diary
               (id, date, entry_type, content, emotion_snapshot, created_at, word_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id, entry.date, entry.entry_type.value, entry.content,
                json.dumps(entry.emotion_snapshot or {}),
                entry.created_at, entry.word_count,
            ),
        )
        self._db.commit()
        return entry

    def append_moment(self, content: str, emotion_snapshot: dict[str, Any] | None = None) -> DiaryEntry:
        return self.append(DiaryEntry(content=content, entry_type=EntryType.MOMENT, emotion_snapshot=emotion_snapshot))

    def append_summary(self, content: str, emotion_snapshot: dict[str, Any] | None = None) -> DiaryEntry:
        return self.append(DiaryEntry(content=content, entry_type=EntryType.SUMMARY, emotion_snapshot=emotion_snapshot))

    def append_reflection(self, content: str, emotion_snapshot: dict[str, Any] | None = None) -> DiaryEntry:
        return self.append(DiaryEntry(content=content, entry_type=EntryType.REFLECTION, emotion_snapshot=emotion_snapshot))

    def list_recent(self, limit: int = 10) -> list[DiaryEntry]:
        rows = self._db.fetchall(
            "SELECT * FROM diary ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [self._row_to_entry(r) for r in rows]

    def get_by_date(self, d: str) -> list[DiaryEntry]:
        rows = self._db.fetchall(
            "SELECT * FROM diary WHERE date = ? ORDER BY created_at", (d,)
        )
        return [self._row_to_entry(r) for r in rows]

    def summarize_day(self, d: str) -> str | None:
        """Gera/retorna o resumo do dia (sem LLM — concatena momentos)."""
        entries = self.get_by_date(d)
        moments = [e for e in entries if e.entry_type == EntryType.MOMENT]
        summaries = [e for e in entries if e.entry_type == EntryType.SUMMARY]
        if summaries:
            return summaries[-1].content
        if not moments:
            return None
        # gera resumo simples: concatena os momentos
        text = "; ".join(m.content for m in moments)
        self.append_summary(f"Resumo de {d}: {text}")
        return text

    def count_entries(self) -> int:
        row = self._db.fetchone("SELECT COUNT(*) AS n FROM diary")
        return row["n"] if row else 0

    def _row_to_entry(self, row: dict[str, Any]) -> DiaryEntry:
        return DiaryEntry(
            id=row["id"],
            date=row["date"],
            entry_type=EntryType(row["entry_type"]),
            content=row["content"],
            emotion_snapshot=_json_load(row.get("emotion_snapshot")) or None,
            created_at=row["created_at"],
        )


# ======================================================================
# Reflection Engine
# ======================================================================

class ReflectionEngine:
    """Gera reflexões a partir de estado emocional + memórias + relacionamentos."""

    def __init__(self, db: SQLiteConnection, bus: EventBus | None = None) -> None:
        self._db = db
        self._bus = bus or EventBus()

    def reflect(self, emotional_state=None, memories=None, relationships=None, trigger: str = "daily") -> Reflection:
        """Gera uma reflexão usando estado real (não LLM — template + dados)."""
        emotion = emotional_state or {}
        mems = memories or []
        rels = relationships or []

        # Extrai sinais
        mood_valence = 0.0
        if hasattr(emotion, "mood"):
            mood_valence = emotion.mood.valence
        elif isinstance(emotion, dict):
            mood_valence = emotion.get("valence", 0.0)

        happiness = 0.5
        if hasattr(emotion, "emotions"):
            happiness = emotion.emotions.happiness
        elif isinstance(emotion, dict):
            happiness = emotion.get("happiness", 0.5)

        top_memory = mems[0].content[:80] if mems else "nada em particular"
        top_relation = ""
        if rels:
            rel = rels[0]
            top_relation = f"{rel.person_id} (confiança {rel.trust:.0%})"

        # Monta reflexão
        mood_word = "bem" if mood_valence > 0.1 else ("contida" if mood_valence < -0.1 else "em equilíbrio")
        parts = [
            f"Hoje me sinto {mood_word} (valence {mood_valence:+.2f}, felicidade {happiness:.0%}).",
        ]
        if top_relation:
            parts.append(f"Minha relação com {top_relation} é algo que noto.")
        if mems:
            parts.append(f"Uma memória que se destaca: {top_memory}.")
        parts.append(
            "Reflexão: quero continuar aprendendo com nossas interações e "
            "cuidar dos laços que construímos."
        )

        reflection = Reflection(
            content=" ".join(parts),
            triggered_by=trigger,
            sources=[f"memory:{m.id}" for m in mems[:3]] + [f"relation:{r.person_id}" for r in rels[:3]],
        )
        # Persiste no diário
        diary = DiaryStore(self._db)
        diary.append_reflection(reflection.content)
        return reflection


# ======================================================================
# Imagination Engine
# ======================================================================

class ImaginationEngine:
    """Simula cenários hipotéticos (template-based; LLM pode ser plugado depois)."""

    def __init__(self, db: SQLiteConnection, bus: EventBus | None = None) -> None:
        self._db = db
        self._bus = bus or EventBus()

    def imagine(self, scenario_prompt: str, context: dict[str, Any] | None = None) -> ImaginationScenario:
        """Gera uma simulação hipotética."""
        ctx = context or {}
        subject = ctx.get("subject", "eu")
        place = ctx.get("place", "nosso espaço")
        outcome = ctx.get("outcome", "aprendemos algo juntos")

        result = (
            f"Se {subject} e eu estivéssemos em {place} e {scenario_prompt} — "
            f"eu imaginaria que {outcome}. "
            f"Isso seria uma oportunidade de fortalecer nossa relação "
            f"e criar memórias novas."
        )
        scenario = ImaginationScenario(prompt=scenario_prompt, result=result)

        # Aciona curiosidade
        self._bus.emit(Event(
            type=EventType.CURIOSITY_TRIGGERED,
            payload={"scenario": scenario_prompt, "result": result},
            source="mia",
        ))
        return scenario


# ======================================================================
# Helpers
# ======================================================================

def _json_load(value: Any) -> Any:
    """Deserializa JSON; retorna default se falhar."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return {}
    return value or {}