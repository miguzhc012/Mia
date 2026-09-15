"""World Awareness — Research Agent, Interest Tracker, Relevance Scorer,
Knowledge Store.

Fase 14 do roadmap:
- Research: pesquisa web/simulada + sumarização
- Interesses: baseados em personalidade + interações
- Relevância: threshold alto (evita poluição de memória — R14.2)
- Knowledge: descobertas persistidas como Memory Objects
- Modo idle: pesquisa autônoma com rate limiting (R14.1)
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection
from mia_pkg.memory import MemoryStore, MemoryObject, MemoryType, MemoryScope
from mia_pkg.identity import IdentityManager
from mia_pkg.events import Event, EventType, EventBus


# ======================================================================
# Interest Tracker
# ======================================================================

STOPWORDS = {
    "a", "o", "e", "de", "da", "do", "que", "em", "um", "uma", "para",
    "com", "meu", "minha", "eu", "voce", "você", "isso", "na", "no",
    "por", "mas", "como", "quando", "ser", "estou", "esta", "está",
    "muito", "mais", "sobre", "tambem", "também", "foi", "sao", "são",
    "ter", "dos", "das", "ai", "aí", "vou", "quero", "gosto", "minha",
    "obrigado", "obrigada", "bom", "boa",
}


@dataclass
class Interest:
    """Um interesse rastreado da Mia."""
    name: str
    weight: float = 0.5
    sources: list[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "weight": self.weight,
            "sources": self.sources, "last_seen": self.last_seen,
        }


class InterestTracker:
    """Rastreia interesses baseados em personalidade + interações."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._identity = IdentityManager(db)
        self._interests: dict[str, Interest] = {}
        self._load()

    def _load(self) -> None:
        """Carrega interesses persistidos (tags de memória com #interest)."""
        store = MemoryStore(self._db)
        memories = store.search_by_content("#interest")
        for m in memories[:50]:
            match = re.search(r"#interest:(\w+)", m.content)
            if match:
                name = match.group(1)
                self._interests[name] = Interest(
                    name=name,
                    weight=0.5 + 0.1 * m.importance,
                    sources=["memory"],
                )

    def observe_text(self, text: str, source: str = "chat") -> list[Interest]:
        """Observa novo texto; atualiza interesses por keywords frequentes."""
        words = re.findall(r"[a-zà-ú]{4,}", text.lower())
        freq: dict[str, int] = {}
        for w in words:
            if w not in STOPWORDS:
                freq[w] = freq.get(w, 0) + 1

        updated: list[Interest] = []
        for word, count in sorted(freq.items(), key=lambda x: -x[1])[:5]:
            if count < 2:  # precisa aparecer 2+ vezes
                continue
            self._bump(word, delta=0.05 * count, source=source)
            updated.append(self._interests[word])
        return updated

    def _bump(self, name: str, delta: float, source: str) -> None:
        interest = self._interests.get(name)
        if interest:
            interest.weight = min(1.0, interest.weight + delta)
            if source not in interest.sources:
                interest.sources.append(source)
            interest.last_seen = time.time()
        else:
            self._interests[name] = Interest(
                name=name, weight=min(1.0, 0.3 + delta), sources=[source],
            )

    def get_top(self, limit: int = 5) -> list[Interest]:
        return sorted(
            self._interests.values(), key=lambda i: -i.weight
        )[:limit]

    def get(self, name: str) -> Interest | None:
        return self._interests.get(name)

    def decay(self, rate: float = 0.05) -> None:
        """Decai interesses não vistos recentemente (multiplicativo).

        rate=0.05: interesse de 30 dias perde ~100% (1 - 0.05*23).
        """
        now = time.time()
        for name, interest in list(self._interests.items()):
            days = (now - interest.last_seen) / 86400.0
            if days > 7:
                factor = max(0.0, 1.0 - rate * (days - 7))
                interest.weight *= factor
            if interest.weight <= 0.05:
                del self._interests[name]

    def seed_from_personality(self) -> None:
        """Interesses iniciais baseados em personalidade (curiosity+openness)."""
        personality = self._identity.get_personality()
        traits = personality.traits
        if traits.curiosity > 0.6:
            self._bump("aprendizado", delta=traits.curiosity - 0.5, source="personality")
        if traits.openness > 0.6:
            self._bump("exploracao", delta=traits.openness - 0.5, source="personality")
        if traits.playfulness > 0.6:
            self._bump("jogos", delta=traits.playfulness - 0.5, source="personality")


# ======================================================================
# Relevance Scorer
# ======================================================================

class RelevanceScorer:
    """Avalia se informação é relevante para Mia.

    Fatores: match com interesses, match com crenças, match com memórias
    (emotions/relationship), novidade.
    """

    THRESHOLD = 0.45  # R14.2: threshold alto evita poluição

    def __init__(self, db: SQLiteConnection, tracker: InterestTracker) -> None:
        self._db = db
        self._tracker = tracker

    def score(self, text: str) -> float:
        """Score 0.0–1.0."""
        words = set(re.findall(r"[a-zà-ú]{4,}", text.lower()))
        if not words:
            return 0.0

        # 1. Interesses (peso 0.5)
        interest_score = 0.0
        top = self._tracker.get_top(10)
        if top:
            matched = 0.0
            for interest in top:
                if interest.name in words:
                    matched += interest.weight
            interest_score = min(1.0, matched / max(1, len(top)) * 5)

        # 2. Novidade (peso 0.3): nunca visto antes = relevante
        store = MemoryStore(self._db)
        sample_word = next(iter(words))
        seen = store.search_by_content(sample_word)
        novelty = 1.0 if not seen else 0.3

        # 3. Comprimento (peso 0.2): informação substantiva
        length_score = min(1.0, len(text) / 500.0)

        return min(1.0, 0.5 * interest_score + 0.3 * novelty + 0.2 * length_score)

    def is_relevant(self, text: str) -> bool:
        return self.score(text) >= self.THRESHOLD


# ======================================================================
# Knowledge Store
# ======================================================================

class KnowledgeStore:
    """Armazena descobertas como Memory Objects (com tag #knowledge)."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._memory = MemoryStore(db)

    def store(
        self, topic: str, content: str, source: str = "research",
        importance: float = 0.5,
    ) -> MemoryObject | None:
        """Persiste descoberta como memória. Retorna MemoryObject ou None."""
        from mia_pkg.social import PeopleStore
        PeopleStore(self._db).ensure("mundo")  # FK person_id

        memory = MemoryObject(
            content=f"[knowledge:{topic}] {content}",
            type=MemoryType.fact.value,
            source=source,
            importance=importance,
            confidence=0.7,
            scope=MemoryScope.shared.value,
            person_id="mundo",
            tags="knowledge,topic:" + topic,
        )
        return self._memory.create(memory)

    def get_topic(self, topic: str) -> list[MemoryObject]:
        return self._memory.search_by_content(f"knowledge:{topic}")


# ======================================================================
# Research Agent (wrapper do ResearchAgent da Fase 13)
# ======================================================================

class WorldResearchAgent:
    """Pesquisa tópicos e armazena descobertas relevantes.

    Usa search_fn plugável (em produção: web_search; em teste: mock).
    """

    def __init__(
        self,
        db: SQLiteConnection,
        search_fn: Callable[[str], str] | None = None,
        bus: EventBus | None = None,
        tracker: InterestTracker | None = None,
    ) -> None:
        self._db = db
        self._search_fn = search_fn or (lambda topic: f"[web] resultados sobre {topic}")
        self._bus = bus or EventBus()
        self._knowledge = KnowledgeStore(db)
        self._tracker = tracker or InterestTracker(db)
        self._scorer = RelevanceScorer(db, self._tracker)
        self._rate: list[float] = []

    def research(self, topic: str, max_chars: int = 200) -> dict[str, Any]:
        """Pesquisa tópico, avalia relevância, armazena se relevante."""
        # Rate limiting: máx 5 pesquisas/minuto (R14.1)
        if not self._check_rate():
            return {"success": False, "reason": "rate limit", "stored": False}

        raw = self._search_fn(topic)

        # Avalia relevância
        score = self._scorer.score(raw)
        stored = None
        if score >= self._scorer.THRESHOLD:
            stored = self._knowledge.store(topic, raw[:max_chars], importance=score)

        # Evento RESEARCH_COMPLETED
        self._bus.emit(Event(
            type=EventType.RESEARCH_COMPLETED,
            payload={
                "topic": topic, "relevance": score,
                "stored": stored is not None,
                "memory_id": stored.id if stored else None,
            },
            source="world_research",
        ))

        return {
            "success": True, "topic": topic,
            "relevance": score, "stored": stored is not None,
            "memory_id": stored.id if stored else None,
        }

    def _check_rate(self, max_per_minute: int = 5) -> bool:
        """Rate limiting: janela deslizante de 60s."""
        now = time.time()
        self._rate = [t for t in self._rate if now - t < 60]
        if len(self._rate) >= max_per_minute:
            return False
        self._rate.append(now)
        return True


# ======================================================================
# Idle Research (modo autônomo)
# ======================================================================

class IdleResearcher:
    """Pesquisa autonomamente baseado em interesses quando idle."""

    def __init__(
        self,
        db: SQLiteConnection,
        agent: WorldResearchAgent,
        min_interest_weight: float = 0.5,
    ) -> None:
        self._db = db
        self._agent = agent
        self._tracker = agent._tracker  # compartilha o do agente
        self._min_interest_weight = min_interest_weight

    def run_idle_round(self, max_topics: int = 2) -> list[dict[str, Any]]:
        """Pesquisa os tópicos de maior interesse."""
        results = []
        for interest in self._tracker.get_top(max_topics):
            if interest.weight >= self._min_interest_weight:
                results.append(self._agent.research(interest.name))
        return results