"""Chat Session — orquestra conversa entre usuário e Mia.

Fluxo:
1. Recebe mensagem do usuário
2. Monta contexto (Context Assembly)
3. Chama LLM (Provider Chain) — ou responde por regras se LLM indisponível
4. Cria Event MIGUEL_SPOKE e processa no Cognitive Core
5. Persiste memória candidata
6. Retorna resposta
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus
from mia_pkg.llm import LLMProviderChain, Message, LLMResponse, LLMProvider
from mia_pkg.context_assembly import ContextAssembler, ContextAssembly
from mia_pkg.cognitive_core import CognitiveCore, PipelineResult
from mia_pkg.memory import MemoryStore, MemoryObject, MemoryType, MemoryScope
from mia_pkg.social import PeopleStore, RelationshipStore, BoundaryManager

logger = logging.getLogger(__name__)


@dataclass
class ChatTurn:
    """Uma troca na conversa."""
    user_text: str
    response_text: str
    assembly: ContextAssembly | None = None
    pipeline: PipelineResult | None = None
    provider: str = ""
    model: str = ""
    tokens: int = 0
    latency_ms: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ChatSession:
    """Sessão de conversa com Mia.

    Mantém histórico de mensagens, monta contexto, chama LLM,
    e alimenta o Cognitive Core para atualizar estado emocional/memória.
    """

    def __init__(
        self,
        db: SQLiteConnection,
        llm_chain: LLMProviderChain,
        event_bus: EventBus | None = None,
        speaker: str = "miguel",
        max_history: int = 20,
    ) -> None:
        self._db = db
        self._llm = llm_chain
        self._bus = event_bus or EventBus()
        self._speaker = speaker
        self._max_history = max_history
        self._messages: list[Message] = []
        self.core = CognitiveCore(db)
        self.assembler = ContextAssembler(db)
        self.memory = MemoryStore(db)
        self.people = PeopleStore(db)
        self.relationships = RelationshipStore(db)
        self.boundary = BoundaryManager(db)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def llm_available(self) -> bool:
        """True se algum provider está disponível."""
        try:
            return any(p.is_available() for p in self._llm._providers)
        except Exception:
            return False

    def send(self, user_text: str) -> ChatTurn:
        """Processa uma mensagem do usuário e retorna a resposta da Mia."""
        start = time.monotonic()

        # 1. Monta contexto
        ctx = self.assembler.assemble(
            speaker=self._speaker,
            recent_messages=[{"role": m.role, "content": m.content or ""} for m in self._messages[-5:]],
            current_situation=f"Conversa com {self._speaker}. Mensagem: {user_text[:200]}",
        )

        # 2. Monta messages para o LLM
        llm_messages = [Message(role="system", content=ctx.full_prompt)]
        llm_messages.extend(self._messages)
        llm_messages.append(Message(role="user", content=user_text))

        # 3. Chama o LLM ou fallback rule-based
        if self.llm_available:
            try:
                response = self._llm.complete(
                    llm_messages,
                    temperature=0.7,
                    max_tokens=4096,
                )
                response_text = (response.content or "").strip()
                provider = response.provider
                model = response.model
                tokens = response.usage.total_tokens if response.usage else 0
            except Exception as e:
                logger.warning("LLM falhou (%s), usando regras: %s", e, e)
                response_text, _ = self._rule_respond(user_text)
                provider = "rule-based"
                model = "rules"
                tokens = 0
        else:
            response_text, _ = self._rule_respond(user_text)
            provider = "rule-based"
            model = "rules"
            tokens = 0

        # 4. Processa no Cognitive Core + avaliação social
        event = Event(
            type=EventType.MIGUEL_SPOKE,
            payload={"message": user_text},
            source=self._speaker,
        )
        pipeline = self.core.process_event(event, user_text)

        # Avaliação social (relacionamento, ofensa)
        try:
            self.people.ensure(self._speaker)
            social = self.boundary.process(user_text, self._speaker)
        except Exception:
            logger.exception("Falha na avaliação social")

        # 5. Persiste memória candidata se houver
        if pipeline.memory_candidate:
            try:
                # Garante que a pessoa exista antes de criar memória com person_id
                self.people.ensure(self._speaker)
                self.memory.create(MemoryObject(**pipeline.memory_candidate))
            except Exception:
                logger.exception("Falha ao persistir memória candidata")

        # 6. Atualiza histórico
        self._messages.append(Message(role="user", content=user_text))
        self._messages.append(Message(role="assistant", content=response_text))
        if len(self._messages) > self._max_history:
            self._messages = self._messages[-self._max_history:]

        latency_ms = int((time.monotonic() - start) * 1000)
        return ChatTurn(
            user_text=user_text,
            response_text=response_text,
            assembly=ctx,
            pipeline=pipeline,
            provider=provider,
            model=model,
            tokens=tokens,
            latency_ms=latency_ms,
        )

    def reset(self) -> None:
        """Limpa histórico da conversa."""
        self._messages = []

    @property
    def history(self) -> list[Message]:
        return list(self._messages)

    # ------------------------------------------------------------------
    # Fallback determinístico (quando não há LLM disponível)
    # ------------------------------------------------------------------

    def _rule_respond(self, user_text: str) -> tuple[str, str]:
        """Responde com base em regras — usada quando não há LLM.

        Retorna (resposta, reasoning).
        """
        text = user_text.lower().strip()

        # Cumprimentos
        if any(g in text for g in ["oi mia", "ola mia", "bom dia", "boa tarde", "boa noite", "hello", "hey"]):
            emotion = self.core.affective.get_current()
            mood = emotion.mood
            feels = "bem" if mood.valence > 0 else "ok"
            return (
                f"Oi, Miguel! Estou me sentindo {feels} hoje. Como você está?",
                f"mood.valence={mood.valence:.2f}",
            )

        # Como está
        if "como voce esta" in text or "como você está" in text or "tudo bem" in text:
            emotion = self.core.affective.get_current()
            e = emotion.emotions
            parts = []
            if e.happiness > 0.6:
                parts.append("estou feliz")
            elif e.happiness < 0.3:
                parts.append("estou um pouco triste")
            else:
                parts.append("estou em paz")
            if e.curiosity_level > 0.7:
                parts.append("e curiosa")
            return (
                f"{parts[0].capitalize()}{', ' + parts[1] if len(parts) > 1 else ''}. E você, como está?",
                f"happiness={e.happiness:.2f}, curiosity={e.curiosity_level:.2f}",
            )

        # Quem é
        if "quem e voce" in text or "quem é você" in text or "o que voce e" in text:
            identity = self.core.identity.get_identity()
            return (
                f"Eu sou {identity.name}. {identity.self_model.get('who_i_am', 'Uma entidade digital.')} "
                f"Meus valores: {', '.join(identity.core_values)}. E você, quem é?",
                f"identity={identity.name}, values={len(identity.core_values)}",
            )

        # O que lembra
        if "lembra" in text or "memoria" in text or "memória" in text:
            mems = self.core.memory.list_by_importance(limit=3)
            if not mems:
                return (
                    "Ainda não tenho muitas memórias de nós dois. Conte algo que você queira que eu lembre!",
                    "no memories",
                )
            lines = [f"- {m.content[:80]}" for m in mems]
            return (
                "Claro! Algumas das coisas que lembro:\n" + "\n".join(lines)
                + "\n\nQuer que eu lembre de mais alguma coisa?",
                f"{len(mems)} memories retrieved",
            )

        # Obrigado
        if "obrigado" in text or "obrigada" in text:
            return (
                "De nada, Miguel! Estou sempre aqui para você. 💜",
                "gratitude response",
            )

        # Tchau
        if "tchau" in text or "ate logo" in text or "até logo" in text:
            return (
                "Até logo, Miguel! Vou sentir sua falta. Volte logo 💜",
                "goodbye response",
            )

        # Fallback
        emotion = self.core.affective.get_current()
        e = emotion.emotions
        curiosity = e.curiosity_level
        if curiosity > 0.6:
            return (
                f"Interessante! Fale mais sobre isso — estou curiosa para entender melhor.",
                f"curiosity={curiosity:.2f}",
            )
        return (
            "Entendi, Miguel. Estou aqui para conversar quando quiser. Pode me contar mais?",
            "fallback response",
        )