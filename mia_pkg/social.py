"""Social — People Store, Relationship Store, Social Evaluator, Boundary Manager.

Fase 5 do roadmap: Mia reconhece e responde diferentemente a diferentes pessoas.
Relacionamentos dimensionais (trust, intimacy, affinity, familiarity),
limites sociais, detecção de ofensa.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus


# ======================================================================
# Dataclasses
# ======================================================================

@dataclass
class Person:
    """Uma pessoa conhecida pela Mia."""
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    first_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """Relacionamento dimensional da Mia com uma pessoa."""
    person_id: str
    trust: float = 0.5
    intimacy: float = 0.0
    affinity: float = 0.5
    familiarity: float = 0.0
    interaction_count: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    history: list[dict[str, Any]] = field(default_factory=list)


class InteractionClass(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class BoundaryResponse(str, Enum):
    NORMAL = "normal"
    WARN = "warn"
    DEFLECT = "deflect"
    REFUSE = "refuse"


@dataclass
class SocialEvaluation:
    """Resultado da avaliação social de uma interação."""
    interaction_class: InteractionClass
    boundary: BoundaryResponse = BoundaryResponse.NORMAL
    reason: str = ""
    should_react: bool = True


# ======================================================================
# People Store
# ======================================================================

class PeopleStore:
    """CRUD de pessoas."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def ensure(self, name: str) -> Person:
        """Garante que uma pessoa existe; cria se não existir. Retorna a pessoa.

        O id é o nome normalizado (lowercase) — assim referências por
        person_id=nome funcionam direto (ex: memórias do cognitive core).
        """
        name = name.strip().lower()
        row = self._db.fetchone("SELECT * FROM people WHERE id = ?", (name,))
        if row:
            return self._row_to_person(row)
        person = Person(id=name, name=name)
        self._db.execute(
            "INSERT INTO people (id, name, first_seen, last_seen, metadata) VALUES (?, ?, ?, ?, ?)",
            (person.id, person.name, person.first_seen, None, json.dumps(person.metadata)),
        )
        self._db.commit()
        return person

    def get(self, person_id: str) -> Person | None:
        row = self._db.fetchone("SELECT * FROM people WHERE id = ?", (person_id,))
        return self._row_to_person(row) if row else None

    def get_by_name(self, name: str) -> Person | None:
        return self.get(name.strip().lower())

    def list(self) -> list[Person]:
        rows = self._db.fetchall("SELECT * FROM people ORDER BY first_seen")
        return [self._row_to_person(r) for r in rows]

    def touch(self, person_id: str) -> None:
        """Atualiza last_seen."""
        self._db.execute(
            "UPDATE people SET last_seen = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), person_id),
        )
        self._db.commit()

    def _row_to_person(self, row: dict[str, Any]) -> Person:
        return Person(
            id=row["id"],
            name=row["name"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            metadata=json.loads(row.get("metadata") or "{}"),
        )


# ======================================================================
# Relationship Store
# ======================================================================

class RelationshipStore:
    """Persistência e evolução de relacionamentos."""

    _DIM_LIMITS = {
        "trust": (0.0, 1.0),
        "intimacy": (0.0, 1.0),
        "affinity": (0.0, 1.0),
        "familiarity": (0.0, 1.0),
    }

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def ensure(self, person_id: str) -> Relationship:
        """Garante um relationship para a pessoa."""
        row = self._db.fetchone(
            "SELECT * FROM relationships WHERE person_id = ?", (person_id,)
        )
        if row:
            return self._row_to_rel(row)
        rel = Relationship(person_id=person_id)
        self._db.execute(
            """INSERT INTO relationships
               (id, person_id, trust, intimacy, affinity, familiarity,
                interaction_count, created_at, updated_at, history)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rel.id, rel.person_id, rel.trust, rel.intimacy, rel.affinity,
                rel.familiarity, rel.interaction_count, rel.created_at,
                rel.updated_at, json.dumps(rel.history),
            ),
        )
        self._db.commit()
        return rel

    def get(self, person_id: str) -> Relationship | None:
        row = self._db.fetchone(
            "SELECT * FROM relationships WHERE person_id = ?", (person_id,)
        )
        return self._row_to_rel(row) if row else None

    def update_dim(self, person_id: str, dim: str, delta: float, reason: str = "") -> Relationship | None:
        """Ajusta uma dimensão do relacionamento por delta (com clamp)."""
        if dim not in self._DIM_LIMITS:
            raise ValueError(f"Dimensão desconhecida: {dim}")
        rel = self.get(person_id) or self.ensure(person_id)
        lo, hi = self._DIM_LIMITS[dim]
        old = getattr(rel, dim)
        new = max(lo, min(hi, old + delta))
        now = datetime.now(timezone.utc).isoformat()
        history = rel.history + [{
            "dim": dim, "old": old, "new": new, "reason": reason, "at": now,
        }]
        rel.interaction_count += 1 if dim in ("trust", "affinity", "intimacy") else 0
        self._db.execute(
            f"""UPDATE relationships
                SET {dim} = ?, interaction_count = ?, updated_at = ?, history = ?
                WHERE person_id = ?""",
            (new, rel.interaction_count, now, json.dumps(history), person_id),
        )
        self._db.commit()
        return self.get(person_id)

    def list_by_affinity(self, limit: int = 10) -> list[Relationship]:
        rows = self._db.fetchall(
            "SELECT * FROM relationships ORDER BY affinity DESC LIMIT ?", (limit,)
        )
        return [self._row_to_rel(r) for r in rows]

    def _row_to_rel(self, row: dict[str, Any]) -> Relationship:
        return Relationship(
            id=row["id"],
            person_id=row["person_id"],
            trust=row["trust"],
            intimacy=row["intimacy"],
            affinity=row["affinity"],
            familiarity=row["familiarity"],
            interaction_count=row["interaction_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            history=json.loads(row.get("history") or "[]"),
        )


# ======================================================================
# Social Evaluator
# ======================================================================

class SocialEvaluator:
    """Classifica interações como positivas, negativas ou neutras.

    Classificador leve baseado em keyword (não LLM).
    """

    _POSITIVE = [
        "obrigado", "obrigada", "amo", "adoro", "gosto", "legal", "ótimo",
        "otimo", "maravilha", "bom", "perfeito", "excelente", "parabéns",
        "parabens", "feliz", "alegre", "gratidão", "gratidao", "valeu",
        "top", "demais", "incrível", "incrivel", "adorável", "adoravel",
        "querida", "querido", "amiga", "amigo", "comprei", "consegui",
    ]
    _NEGATIVE = [
        "odeio", "detesto", "raiva", "triste", "chato", "chata", "burro",
        "burra", "idiota", "estúpido", "estupido", "inútil", "inutil",
        "feio", "feia", "horrível", "horrivel", "péssimo", "pessimo",
        "ruim", "odeio", "ódio", "odio", "insulto", "ofensa", "calado",
        "cala a boca", "cala boca", "vai se fuder", "vai pro inferno",
        "merda", "desprezível", "desprezivel", "incompetente",
    ]
    _OFFENSIVE = [
        "cala a boca", "cala boca", "idiota", "burro", "burra", "estúpido",
        "estupido", "inútil", "inutil", "feia", "feio", "vai se fuder",
        "fdp", "desgraçado", "desgracado", "seu lixo", "sua lixo",
        "vai pro inferno", "incompetente", "otária", "otario",
        "arrombado", "arrombada",
    ]

    def __init__(self) -> None:
        self._insults: set[str] = set(self._OFFENSIVE)

    def evaluate(self, text: str) -> SocialEvaluation:
        """Classifica a interação."""
        t = text.lower().strip()

        for insult in self._insults:
            if insult in t:
                return SocialEvaluation(
                    interaction_class=InteractionClass.NEGATIVE,
                    boundary=BoundaryResponse.REFUSE,
                    reason=f"ofensa detectada: {insult}",
                )

        pos_hits = sum(1 for w in self._POSITIVE if w in t)
        neg_hits = sum(1 for w in self._NEGATIVE if w in t)

        if pos_hits > neg_hits:
            return SocialEvaluation(
                interaction_class=InteractionClass.POSITIVE,
                reason=f"+{pos_hits} positivos, -{neg_hits} negativos",
            )
        if neg_hits > pos_hits:
            return SocialEvaluation(
                interaction_class=InteractionClass.NEGATIVE,
                reason=f"+{pos_hits} positivos, -{neg_hits} negativos",
            )
        return SocialEvaluation(
            interaction_class=InteractionClass.NEUTRAL,
            reason="sem sinal forte",
        )

    def add_insult(self, word: str) -> None:
        """Adiciona palavra à lista de ofensas."""
        self._insults.add(word.lower())


# ======================================================================
# Boundary Manager
# ======================================================================

class BoundaryManager:
    """Gerencia limites sociais e respostas a ofensas."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self.evaluator = SocialEvaluator()

    def process(self, text: str, speaker: str) -> SocialEvaluation:
        """Processa uma interação social: avalia e ajusta relacionamento."""
        from mia_pkg.needs_desires import NeedsDesiresStore
        people = PeopleStore(self._db)
        rel_store = RelationshipStore(self._db)

        person = people.ensure(speaker)
        rel = rel_store.ensure(person.id)
        eval_ = self.evaluator.evaluate(text)

        if eval_.interaction_class == InteractionClass.POSITIVE:
            rel_store.update_dim(person.id, "trust", 0.05, "interação positiva")
            rel_store.update_dim(person.id, "affinity", 0.08, "interação positiva")
            rel_store.update_dim(person.id, "familiarity", 0.05, "contato")
        elif eval_.interaction_class == InteractionClass.NEGATIVE:
            if eval_.boundary == BoundaryResponse.REFUSE:
                rel_store.update_dim(person.id, "trust", -0.15, "ofensa")
                rel_store.update_dim(person.id, "affinity", -0.12, "ofensa")
            else:
                rel_store.update_dim(person.id, "trust", -0.05, "interação negativa")
                rel_store.update_dim(person.id, "affinity", -0.03, "interação negativa")
        else:
            rel_store.update_dim(person.id, "familiarity", 0.03, "contato neutro")

        people.touch(person.id)
        return eval_


# ======================================================================
# Integração: SocialContext no Cognitive Core
# ======================================================================

def integrate_social(db: SQLiteConnection, event: Event, text: str) -> SocialEvaluation:
    """Integra avaliação social no pipeline de evento.

    Retorna avaliação; emite eventos INSULT_RECEIVED/COMPLIMENT_RECEIVED.
    """
    if event.source is None:
        return SocialEvaluation(InteractionClass.NEUTRAL, reason="sem speaker")

    boundary = BoundaryManager(db)
    eval_ = boundary.process(text, event.source)

    if eval_.interaction_class == InteractionClass.NEGATIVE and eval_.boundary == BoundaryResponse.REFUSE:
        # Evento de ofensa
        insult_event = Event(
            type=EventType.INSULT_RECEIVED,
            payload={"text": text, "evaluation": eval_.reason},
            source=event.source,
        )
        event_bus = getattr(db, "_event_bus", None)
    elif eval_.interaction_class == InteractionClass.POSITIVE:
        compliment_event = Event(
            type=EventType.COMPLIMENT_RECEIVED,
            payload={"text": text, "evaluation": eval_.reason},
            source=event.source,
        )
    return eval_