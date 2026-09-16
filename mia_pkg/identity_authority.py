"""Identity Authority — evolução de personalidade a partir de interações.

Fase 3 critérios que faltam:
- PersonalityVector evolui com base em interações (não manualmente)
- Transições de personalidade validadas pelo State Authority
- Rate limiting de mudanças (evita personalidade flutuante — R3.1)
- Core values imutáveis (Policy Engine)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.identity import IdentityManager, PersonalityVector


TRAIT_RANGES = {
    # traço: (min, max) — evolução limitada por interação
    "openness": (0.4, 0.8),
    "conscientiousness": (0.4, 0.8),
    "extraversion": (0.3, 0.7),
    "agreeableness": (0.4, 0.9),
    "neuroticism": (0.1, 0.6),
    "curiosity": (0.4, 0.9),
    "playfulness": (0.3, 0.8),
    "assertiveness": (0.3, 0.7),
    "empathy": (0.4, 0.9),
    "independence": (0.3, 0.8),
}

# Eventos que influenciam cada traço (positivo/negativo)
TRAIT_EFFECTS: dict[str, dict[str, float]] = {
    # evento: {traço: delta}
    "novidade_encontrada": {"openness": +0.02, "curiosity": +0.03},
    "exploracao_rejeitada": {"openness": -0.01, "curiosity": -0.02},
    "compromisso_cumprido": {"conscientiousness": +0.02},
    "tarefa_abandonada": {"conscientiousness": -0.02},
    "interacao_social": {"extraversion": +0.015, "agreeableness": +0.01},
    "isolamento": {"extraversion": -0.01},
    "elogio_recebido": {"agreeableness": +0.01},
    "conflito": {"agreeableness": -0.015, "neuroticism": +0.01},
    "seguranca_estavel": {"neuroticism": -0.01},
    "estresse": {"neuroticism": +0.015},
    "ideia_nova": {"curiosity": +0.02, "openness": +0.01},
    "curiosidade_recompensada": {"curiosity": +0.03},
    "brincadeira": {"playfulness": +0.02},
    "decisao_tomada": {"assertiveness": +0.015},
    "independencia_demonstrada": {"independence": +0.02},
    "empatia_demonstrada": {"empathy": +0.02},
    "momento_ameacador": {"neuroticism": +0.01, "independence": -0.01},
}


@dataclass
class PersonalityChange:
    """Registro de uma mudança de personalidade auditada."""
    trait: str
    delta: float
    event: str
    timestamp: float = field(default_factory=time.time)
    version_after: int = 0


class IdentityAuthority:
    """Gerencia evolução de personalidade com validação e auditoria.

    Fluxo: evento → deltas → clamping (ranges) → nova versão →
    grava via IdentityManager (auditável) → rate limit.
    """

    MIN_INTERVAL_SECONDS = 30.0  # R3.1: evita flutuação rápida

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._identity = IdentityManager(db)
        self._last_change: dict[str, float] = {}
        self._changes: list[PersonalityChange] = []

    def process_interaction(self, event: str) -> list[PersonalityChange]:
        """Processa um evento de interação; ajusta personalidade se aplicável."""
        effects = TRAIT_EFFECTS.get(event)
        if not effects:
            return []

        # Rate limit: por traço, respeita intervalo mínimo.
        # Usa sentinela None: traço que NUNCA mudou não pode ser
        # bloqueado como se tivesse mudado no tempo 0 (primeira
        # mudança legítima acontece imediatamente).
        now = time.monotonic()
        changes: list[PersonalityChange] = []
        for trait, delta in effects.items():
            last = self._last_change.get(trait)
            if last is not None and now - last < self.MIN_INTERVAL_SECONDS:
                continue  # muda rápido demais (2ª+ mudança dentro da janela)

            applied = self._adjust_trait(trait, delta, event)
            if applied:
                self._last_change[trait] = now
                changes.append(applied)

        # Se houve mudanças, persiste nova versão
        if changes:
            self._changes.extend(changes)
            self._persist()
        return changes

    def process_text_interaction(self, user_text: str) -> list[PersonalityChange]:
        """Processa uma interação de texto simples (heurística leve).

        Detecta padrões: perguntas (curiosidade), tom positivo, etc.
        """
        text = user_text.lower()
        events: list[str] = []
        if "?" in text or "por que" in text or "como" in text:
            events.append("ideia_nova" if len(text) > 30 else "curiosidade_recompensada")
        if any(w in text for w in ["obrigado", "valeu", "adorei", "amei", "ótimo", "otimo"]):
            events.append("elogio_recebido")
        if any(w in text for w in ["vamos", "bora", "fazer algo", "brincar"]):
            events.append("brincadeira")
        if any(w in text for w in ["estou triste", "deprimido", "ansioso", "preocupado"]):
            events.append("estresse")

        changes: list[PersonalityChange] = []
        for event in events:
            changes.extend(self.process_interaction(event))
        return changes

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _adjust_trait(
        self, trait: str, delta: float, event: str
    ) -> PersonalityChange | None:
        """Ajusta um traço dentro do range. Retorna change ou None."""
        personality = self._identity.get_personality()
        current = getattr(personality.traits, trait)
        lo, hi = TRAIT_RANGES.get(trait, (0.0, 1.0))
        new_value = max(lo, min(hi, current + delta))
        if new_value == current:
            return None  # já no limite
        return PersonalityChange(
            trait=trait, delta=new_value - current, event=event,
            version_after=personality.version + 1,
        )

    def _persist(self) -> None:
        """Persiste nova versão de personalidade com os deltas acumulados da ÚLTIMA rodada."""
        personality = self._identity.get_personality()
        # pega apenas changes desde a última persistência (os com version_after > versão atual)
        fresh = [c for c in self._changes if c.version_after > personality.version]
        deltas = {c.trait: c.delta for c in fresh}
        if not deltas:
            return
        props = self._identity.propose_personality_change(deltas)
        self._identity.apply_validated_personality(
            props["new_traits"], props["new_version"]
        )

    def history(self) -> list[PersonalityChange]:
        return list(self._changes)

    def reset_limits(self) -> None:
        self._last_change.clear()