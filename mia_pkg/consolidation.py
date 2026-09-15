"""Memory Consolidation — conversas → Memory Objects + Scheduler.

Fase 2 do roadmap:
- Consolidação: após N turns, converte conversa em memória resumida
- Retrieval melhorado: ranking por importância × recência × frequência
- Associations: liga memórias relacionadas
- Scheduler: consolidação periódica + limpeza de memórias expiradas
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.memory import MemoryStore, MemoryObject, MemoryType, MemoryScope


# ======================================================================
# Retrieval melhorado
# ======================================================================

def tokenize(text: str) -> list[str]:
    """Tokeniza texto simples (lowercase, remove pontuação)."""
    return re.findall(r"[a-zà-ú0-9]+", text.lower())


class RetrievalEngine:
    """Busca com ranking: importância × recência × frequência de termos."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._store = MemoryStore(db)

    def search(self, query: str, limit: int = 5, min_importance: float = 0.0) -> list[MemoryObject]:
        """Busca memórias por keywords, rankeando por importância × recência."""
        terms = tokenize(query)
        if not terms:
            return self._store.list_by_importance(limit=limit)

        rows = self._db.fetchall(
            "SELECT * FROM memory_objects WHERE importance >= ? ORDER BY importance DESC",
            (min_importance,),
        )
        objs = [self._store._row_to_obj(r) for r in rows]

        # Score: importância (0.5) + match de termos (0.3) + recência (0.2)
        scored = []
        for obj in objs:
            content_terms = tokenize(obj.content)
            matches = sum(1 for t in terms if t in content_terms)
            term_score = matches / len(terms) if terms else 0

            # recência (0-1): mais recente = mais próximo de 1
            try:
                created = datetime.fromisoformat(obj.created_at)
                age_days = (datetime.now(timezone.utc) - created).days
                recency = max(0.0, 1.0 - age_days / 30.0)  # decai em 30 dias
            except Exception:
                recency = 0.5

            score = 0.5 * obj.importance + 0.3 * term_score + 0.2 * recency
            if matches > 0 or obj.importance >= 0.7:
                scored.append((score, obj))

        scored.sort(key=lambda x: -x[0])
        return [obj for _, obj in scored[:limit]]


# ======================================================================
# Memory Associations
# ======================================================================

class MemoryAssociations:
    """Liga memórias relacionadas (memory_associations)."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def associate(self, memory_id: str, other_id: str) -> None:
        """Cria associação bidirecional entre memórias."""
        now = datetime.now(timezone.utc).isoformat()
        for a, b in ((memory_id, other_id), (other_id, memory_id)):
            exists = self._db.fetchone(
                "SELECT 1 FROM memory_associations WHERE memory_id=? AND associated_id=?",
                (a, b),
            )
            if not exists:
                self._db.execute(
                    "INSERT INTO memory_associations (memory_id, associated_id, strength, created_at) VALUES (?, ?, ?, ?)",
                    (a, b, 0.5, now),
                )
        self._db.commit()

    def get_associations(self, memory_id: str) -> list[str]:
        """Retorna IDs das memórias associadas."""
        rows = self._db.fetchall(
            "SELECT associated_id FROM memory_associations WHERE memory_id = ?",
            (memory_id,),
        )
        return [r["associated_id"] for r in rows]

    def find_related(self, memory_id: str, limit: int = 5) -> list[MemoryObject]:
        """Retorna memórias relacionadas por associação."""
        store = MemoryStore(self._db)
        related: list[MemoryObject] = []
        for assoc_id in self.get_associations(memory_id):
            row = self._db.fetchone(
                "SELECT * FROM memory_objects WHERE id = ?", (assoc_id,)
            )
            if row:
                related.append(store._row_to_obj(row))
            if len(related) >= limit:
                break
        return related


# ======================================================================
# Memory Consolidation
# ======================================================================

class MemoryConsolidator:
    """Converte conversas longas em Memory Objects resumidos.

    Estratégia: após N turns, pega as mensagens, agrupa por tema,
    e cria memórias consolidadas (is_consolidated=True).
    """

    def __init__(self, db: SQLiteConnection, turns_threshold: int = 8) -> None:
        self._db = db
        self._store = MemoryStore(db)
        self._assoc = MemoryAssociations(db)
        self._turns_threshold = turns_threshold

    def _ensure_person(self, speaker: str) -> None:
        """Garante que a pessoa exista antes de criar memória com person_id."""
        if not speaker:
            return
        from mia_pkg.social import PeopleStore
        PeopleStore(self._db).ensure(speaker)

    def consolidate_conversation(
        self,
        messages: list[dict[str, str]],
        speaker: str = "miguel",
    ) -> list[MemoryObject]:
        """Consolida conversa em memórias.

        messages: [{role: user|assistant, content: str}]
        Retorna as memórias consolidadas criadas.
        """
        if len(messages) < self._turns_threshold:
            return []  # conversa curta demais

        # Garante que a pessoa exista (FK people.id)
        self._ensure_person(speaker)

        # Extrai as falas do usuário (o que importa para memória de relação)
        user_lines = [
            m["content"] for m in messages
            if m.get("role") == "user" and m.get("content")
        ]
        if not user_lines:
            return []

        # Summary simples: concatena as falas do usuário
        summary_text = " | ".join(line.strip()[:120] for line in user_lines[:10])

        # Busca memórias existentes parecidas para associar
        created: list[MemoryObject] = []
        for topic in self._extract_topics(summary_text):
            memory = MemoryObject(
                content=f"[consolidado] Sobre {topic}: {summary_text[:200]}",
                type=MemoryType.experience.value,
                source="consolidation",
                importance=0.6,   # consolidação é moderadamente importante
                confidence=0.6,
                scope=MemoryScope.shared.value,
                person_id=speaker,
                is_consolidated=True,
            )
            self._store.create(memory)
            created.append(memory)

        # Associa as novas memórias entre si
        for i in range(len(created) - 1):
            self._assoc.associate(created[i].id, created[i + 1].id)

        return created

    def _extract_topics(self, text: str) -> list[str]:
        """Extrai tópicos de um texto (keywords mais frequentes)."""
        words = tokenize(text)
        stopwords = {
            "a", "o", "e", "de", "da", "do", "que", "em", "um", "uma",
            "para", "com", "meu", "minha", "eu", "voce", "você", "isso",
            "aquilo", "na", "no", "por", "mas", "como", "quando", "ser",
            "estou", "esta", "está", "muito", "mais", "sobre", "tambem",
            "também", "foi", "sao", "são", "ter", "dos", "das", "ai", "aí",
        }
        freq: dict[str, int] = {}
        for w in words:
            if w not in stopwords and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1
        # top 3 keywords como tópicos
        top = sorted(freq.items(), key=lambda x: -x[1])[:3]
        return [w for w, _ in top if top]


# ======================================================================
# Scheduler (consolidação periódica + limpeza)
# ======================================================================

class MemoryScheduler:
    """Tarefas periódicas: consolidação e limpeza de memórias expiradas."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._store = MemoryStore(db)
        self._consolidator = MemoryConsolidator(db)

    def cleanup_expired(
        self, max_age_days: int = 90, min_importance: float = 0.3
    ) -> int:
        """Remove memórias antigas de baixa importância (retention policy).

        Retorna quantas memórias foram removidas.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        rows = self._db.fetchall(
            "SELECT id FROM memory_objects "
            "WHERE created_at < ? AND importance < ? AND is_consolidated = 0",
            (cutoff, min_importance),
        )
        for row in rows:
            self._store.delete(row["id"])
        return len(rows)

    def decay_access(self, decay_rate: float = 0.01) -> None:
        """Aplica decaimento de importância para memórias não acessadas.

        Memórias não acessadas há muito tempo perdem importância.
        """
        rows = self._db.fetchall(
            "SELECT id, importance, access_count, last_accessed_at FROM memory_objects"
        )
        now = datetime.now(timezone.utc)
        for row in rows:
            penalty = 0.0
            if row["last_accessed_at"]:
                try:
                    last = datetime.fromisoformat(row["last_accessed_at"])
                    days = (now - last).days
                    penalty = min(decay_rate * max(0, days - 7), 0.2)
                except Exception:
                    pass
            new_importance = max(0.0, row["importance"] - penalty)
            if new_importance != row["importance"]:
                self._db.execute(
                    "UPDATE memory_objects SET importance = ? WHERE id = ?",
                    (new_importance, row["id"]),
                )
        self._db.commit()

    def run_daily_maintenance(
        self, max_age_days: int = 90, min_importance: float = 0.3
    ) -> dict[str, int]:
        """Roda tarefas de manutenção. Retorna {cleanup: N, decay: N}."""
        removed = self.cleanup_expired(max_age_days, min_importance)
        before_row = self._db.fetchone("SELECT COUNT(*) AS n FROM memory_objects")
        before = before_row["n"] if before_row else 0
        self.decay_access()
        after_row = self._db.fetchone("SELECT COUNT(*) AS n FROM memory_objects")
        after = after_row["n"] if after_row else 0
        return {"cleanup": removed, "count_before": before, "count_after": after}