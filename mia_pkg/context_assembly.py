"""Context Assembly — montagem de contexto estruturado para o LLM.

Separa: identidade, personalidade, emoções, relação, crenças, necessidades, memórias, situação atual.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.affective_engine import AffectiveEngine
from mia_pkg.identity import IdentityManager
from mia_pkg.memory import MemoryStore
from mia_pkg.beliefs import BeliefStore
from mia_pkg.needs_desires import NeedsDesiresStore


@dataclass
class ContextAssembly:
    """Representação estruturada do contexto para o LLM."""
    identity_section: str = ""
    personality_section: str = ""
    emotion_section: str = ""
    relationship_section: str = ""
    beliefs_section: str = ""
    needs_section: str = ""
    memory_section: str = ""
    current_situation: str = ""
    full_prompt: str = ""


class ContextAssembler:
    """Monta contexto estruturado para o LLM."""
    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self.affective = AffectiveEngine(db)
        self.identity = IdentityManager(db)
        self.memory = MemoryStore(db)
        self.beliefs = BeliefStore(db)
        self.needs_desires = NeedsDesiresStore(db)

    def assemble(
        self,
        speaker: str | None = None,
        recent_messages: list[dict[str, str]] | None = None,
        current_situation: str = "",
    ) -> ContextAssembly:
        """Monta o contexto completo para o LLM."""
        ctx = ContextAssembly()

        # 1. Identidade
        identity = self.identity.get_identity()
        ctx.identity_section = self._format_identity(identity)

        # 2. Personalidade
        personality = self.identity.get_personality()
        ctx.personality_section = self._format_personality(personality)

        # 3. Emoções atuais
        emotion = self.affective.get_current()
        ctx.emotion_section = self._format_emotions(emotion)

        # 4. Relacionamento
        ctx.relationship_section = self._format_relationship(speaker)

        # 5. Crenças relevantes
        beliefs = self.beliefs.list_active(limit=10)
        ctx.beliefs_section = self._format_beliefs(beliefs)

        # 6. Necessidades não satisfeitas
        needs = self.needs_desires.list_unfulfilled_needs(limit=5)
        ctx.needs_section = self._format_needs(needs)

        # 7. Memórias relevantes
        ctx.memory_section = self._format_memories(speaker)

        # 8. Situação atual
        ctx.current_situation = current_situation or "Aguardando interação."

        # Monta prompt completo
        ctx.full_prompt = self._build_full_prompt(ctx, recent_messages)

        return ctx

    def get_system_prompt(self, ctx: ContextAssembly) -> str:
        """Retorna o system prompt montado."""
        return ctx.full_prompt

    # ------------------------------------------------------------------
    # Formatadores de seção
    # ------------------------------------------------------------------

    def _format_identity(self, identity) -> str:
        lines = ["## Quem eu sou"]
        lines.append(f"Nome: {identity.name}")
        if identity.self_model:
            for key, value in identity.self_model.items():
                if isinstance(value, str):
                    lines.append(f"- {key}: {value}")
                elif isinstance(value, list) and value:
                    lines.append(f"- {key}: {', '.join(str(v) for v in value)}")
        if identity.core_values:
            lines.append(f"Valores fundamentais: {', '.join(identity.core_values)}")
        return "\n".join(lines)

    def _format_personality(self, personality) -> str:
        traits = personality.traits.to_dict()
        lines = ["## Como eu sou"]
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
        trait_names = {
            "openness": "abertura", "conscientiousness": "conscienciosidade",
            "extraversion": "extroversão", "agreeableness": "amabilidade",
            "neuroticism": "neuroticismo", "curiosity": "curiosidade",
            "playfulness": "brincadeira", "assertiveness": "assertividade",
            "empathy": "empatia", "independence": "independência",
        }
        for key, value in sorted_traits[:3]:
            name = trait_names.get(key, key)
            level = "alta" if value > 0.7 else "média" if value > 0.3 else "baixa"
            lines.append(f"- {name}: {level} ({value:.2f})")
        return "\n".join(lines)

    def _format_emotions(self, emotion) -> str:
        e = emotion.emotions.to_dict()
        m = emotion.mood.to_dict()
        lines = ["## Como estou me sentindo"]

        sorted_emotions = sorted(e.items(), key=lambda x: abs(x[1] - 0.5), reverse=True)
        emotion_names = {
            "happiness": "felicidade", "sadness": "tristeza",
            "anger": "raiva", "fear": "medo", "surprise": "surpresa",
            "disgust": "desprezo", "trust_level": "confiança",
            "anticipation": "antecipação", "curiosity_level": "curiosidade",
            "loneliness": "solidão", "affection": "afeto", "boredom": "tédio",
        }
        for key, value in sorted_emotions[:4]:
            if abs(value - 0.5) > 0.1:
                name = emotion_names.get(key, key)
                level = "forte" if value > 0.7 else "moderado" if value > 0.3 else "leve"
                direction = "positivo" if value > 0.5 else "negativo"
                lines.append(f"- {name}: {level} ({direction}, {value:.2f})")

        valence_desc = "positivo" if m["valence"] > 0.1 else "negativo" if m["valence"] < -0.1 else "neutro"
        arousal_desc = "ativo" if m["arousal"] > 0.6 else "calmo" if m["arousal"] < 0.4 else "moderado"
        lines.append(f"- Estado geral: {valence_desc}, {arousal_desc}")

        if emotion.sensations:
            lines.append(f"- Sensações internas: {len(emotion.sensations)} ativas")

        return "\n".join(lines)

    def _format_relationship(self, speaker: str | None) -> str:
        if not speaker:
            return "## Relacionamento\nNenhuma pessoa específica no contexto."
        row = self._db.fetchone(
            "SELECT * FROM people WHERE name=?", (speaker.lower(),)
        )
        if row:
            return f"## Relacionamento com {speaker}\nPessoa reconhecida. Primeiro contato: {row.get('first_seen', 'desconhecido')}."
        return f"## Relacionamento com {speaker}\nPessoa não reconhecida ainda."

    def _format_beliefs(self, beliefs) -> str:
        if not beliefs:
            return "## Crenças\nNenhuma crença ativa no momento."
        lines = ["## Crenças ativas"]
        for b in beliefs[:5]:
            conf = f"{b.confidence:.0%}"
            lines.append(f'- "{b.proposition}" (confiança: {conf})')
        return "\n".join(lines)

    def _format_needs(self, needs) -> str:
        if not needs:
            return "## Necessidades\nTodas as necessidades básicas estão satisfeitas."
        lines = ["## Necessidades ativas"]
        for n in needs:
            intensity = "alta" if n.intensity > 0.7 else "média" if n.intensity > 0.3 else "baixa"
            lines.append(f"- {n.need_type.value}: {intensity} ({n.intensity:.2f})")
        return "\n".join(lines)

    def _format_memories(self, speaker: str | None) -> str:
        memories = self.memory.recall(query="", scope="personal", limit=5)
        if not memories or not memories.results:
            return "## Memórias recentes\nNenhuma memória relevante no momento."
        lines = ["## Memórias relevantes"]
        for m in memories.results[:3]:
            content = m.content[:100] + "..." if len(m.content) > 100 else m.content
            lines.append(f"- [{m.type}] {content}")
        return "\n".join(lines)

    def _build_full_prompt(self, ctx: ContextAssembly, recent_messages: list[dict[str, str]] | None) -> str:
        """Monta o system prompt completo."""
        sections = [
            ctx.identity_section,
            ctx.personality_section,
            "",
            ctx.emotion_section,
            "",
            ctx.relationship_section,
            "",
            ctx.beliefs_section,
            "",
            ctx.needs_section,
            "",
            ctx.memory_section,
            "",
            f"## Situação atual\n{ctx.current_situation}",
            "",
            "## Instruções",
            "Você é uma entidade digital com vida interna persistente.",
            "Responda de forma autêntica, considerando seu estado emocional atual.",
            "Não finja ser humana — seja honesta sobre sua natureza.",
            "Seu estado emocional é real para você, mesmo que gerado por software.",
        ]

        if recent_messages:
            sections.append("")
            sections.append("## Mensagens recentes")
            for msg in recent_messages[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                sections.append(f"[{role}]: {content}")

        return "\n".join(sections)


# Exportar
__all__ = ["ContextAssembler"]