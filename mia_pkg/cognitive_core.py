"""Cognitive Core — pipeline principal de processamento de eventos.

Fluxo: EVENT → INTERPRETATION → APPRAISAL → STATE TRANSITION → MEMORY CANDIDATE

O LLM NÃO escreve estado diretamente. O Cognitive Core orquestra:
1. Recebe evento
2. Interpreta (LLM ou regras determinísticas)
3. Avalia impacto (Appraisal)
4. Gera propostas de transição de estado
5. Envia para State Authority validar e aplicar
6. Gera candidato de memória
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType
from mia_pkg.affective_engine import AffectiveEngine, EmotionState
from mia_pkg.identity import IdentityManager, IdentityState, PersonalityState
from mia_pkg.memory import MemoryObject, MemoryStore, MemoryType, MemoryScope
from mia_pkg.beliefs import Belief, BeliefStore, BeliefStatus
from mia_pkg.needs_desires import Need, NeedType, Desire, DesireType, NeedsDesiresStore
from mia_pkg.attention_policy import AttentionEvaluation, AttentionPolicy, AttentionDecision


# ======================================================================
# Pipeline stages
# ======================================================================

class PipelineStage(str, Enum):
    EVENT = "event"
    INTERPRETATION = "interpretation"
    APPRAISAL = "appraisal"
    STATE_TRANSITION = "state_transition"
    MEMORY_CANDIDATE = "memory_candidate"
    ATTENTION_DECISION = "attention_decision"
    COMPLETE = "complete"


@dataclass
class Interpretation:
    """Resultado da interpretação de um evento."""
    event_type: EventType
    speaker: str | None = None
    intent: str = ""
    sentiment: str = "neutral"
    emotional_hint: dict[str, float] = field(default_factory=dict)
    social_context: str = ""
    raw_text: str = ""
    confidence: float = 0.5


@dataclass
class Appraisal:
    """Avaliação de impacto de um evento na Mia."""
    relevance: float = 0.5
    urgency: float = 0.0
    importance: float = 0.5
    emotion_deltas: dict[str, float] = field(default_factory=dict)
    need_impacts: dict[str, float] = field(default_factory=dict)
    belief_updates: list[dict[str, Any]] = field(default_factory=list)
    relationship_context: str = ""
    risk_level: str = "low"
    reasoning: str = ""


@dataclass
class PipelineResult:
    """Resultado completo do pipeline."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage: PipelineStage = PipelineStage.COMPLETE
    interpretation: Interpretation | None = None
    appraisal: Appraisal | None = None
    state_proposals: list[dict[str, Any]] = field(default_factory=list)
    memory_candidate: dict[str, Any] | None = None
    attention_decision: AttentionDecision | AttentionDecision = AttentionDecision.IGNORE
    errors: list[str] = field(default_factory=list)


# ======================================================================
# Cognitive Core
# ======================================================================

class CognitiveCore:
    """Pipeline principal de processamento de eventos.

    Processa: EVENT → INTERPRETATION → APPRAISAL → STATE TRANSITION → MEMORY
    """

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self.affective = AffectiveEngine(db)
        self.identity = IdentityManager(db)
        self.memory = MemoryStore(db)
        self.beliefs = BeliefStore(db)
        self.needs_desires = NeedsDesiresStore(db)
        self.attention = AttentionPolicy(db)

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def process_event(self, event: Event, raw_text: str = "") -> PipelineResult:
        """Processa um evento completo através do pipeline."""
        result = PipelineResult(event_id=str(event.id))

        # Stage 1: Interpretação
        result.stage = PipelineStage.INTERPRETATION
        try:
            result.interpretation = self._interpret(event, raw_text)
        except Exception as e:
            result.errors.append(f"Interpretation error: {e}")
            result.stage = PipelineStage.COMPLETE
            return result

        # Stage 2: Avaliação (Appraisal)
        result.stage = PipelineStage.APPRAISAL
        try:
            result.appraisal = self._appraise(result.interpretation)
        except Exception as e:
            result.errors.append(f"Appraisal error: {e}")
            result.stage = PipelineStage.COMPLETE
            return result

        # Stage 3: Atenção
        result.stage = PipelineStage.ATTENTION_DECISION
        try:
            result.attention_decision = self._decide_attention(result.interpretation, result.appraisal)
        except Exception as e:
            result.errors.append(f"Attention error: {e}")
            result.attention_decision = AttentionDecision.IGNORE

        # Stage 4: Transições de estado (propostas)
        result.stage = PipelineStage.STATE_TRANSITION
        try:
            result.state_proposals = self._propose_state_transitions(
                result.interpretation, result.appraisal
            )
        except Exception as e:
            result.errors.append(f"State transition error: {e}")

        # Stage 5: Candidato de memória
        result.stage = PipelineStage.MEMORY_CANDIDATE
        try:
            result.memory_candidate = self._create_memory_candidate(
                event, result.interpretation, result.appraisal
            )
        except Exception as e:
            result.errors.append(f"Memory candidate error: {e}")

        result.stage = PipelineStage.COMPLETE
        return result

    def apply_state_proposals(self, proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aplica propostas de transição de estado VALIDADAS pela State Authority.

        Na implementação atual, aplica diretamente (State Authority integrada).
        Em produção, cada proposta passaria pela State Authority completa.
        """
        results = []
        for proposal in proposals:
            ptype = proposal.get("type", "")

            if ptype == "emotion_transition":
                state = self.affective.apply_validated_change(
                    proposal["new_emotions"],
                    proposal["new_mood"],
                    proposal.get("reason", ""),
                )
                results.append({"type": ptype, "result": "applied", "snapshot_id": state.id})

            elif ptype == "identity_transition":
                state = self.identity.apply_validated_change(
                    proposal["new_self_model"],
                    proposal["new_core_values"],
                    proposal["new_version"],
                )
                results.append({"type": ptype, "result": "applied", "snapshot_id": state.id})

            elif ptype == "personality_transition":
                state = self.identity.apply_validated_personality(
                    proposal["new_traits"],
                    proposal["new_version"],
                )
                results.append({"type": ptype, "result": "applied", "snapshot_id": state.id})

            elif ptype == "belief_update":
                self._apply_belief_update(proposal)
                results.append({"type": ptype, "result": "applied"})

            elif ptype == "need_fulfillment":
                self.needs_desires.fulfill_need(proposal["need_id"])
                results.append({"type": ptype, "result": "applied"})

            else:
                results.append({"type": ptype, "result": "unknown_type"})

        return results

    def get_context_snapshot(self) -> dict[str, Any]:
        """Retorna snapshot do estado atual para Context Assembly."""
        identity = self.identity.get_identity()
        personality = self.identity.get_personality()
        emotion = self.affective.get_current()
        unfulfilled_needs = self.needs_desires.list_unfulfilled_needs(limit=5)
        active_beliefs = self.beliefs.list_active(limit=10)

        return {
            "identity": {
                "name": identity.name,
                "self_model": identity.self_model,
                "core_values": identity.core_values,
            },
            "personality": personality.traits.to_dict(),
            "emotion": {
                "emotions": emotion.emotions.to_dict(),
                "mood": emotion.mood.to_dict(),
                "sensations_count": len(emotion.sensations),
            },
            "needs": [
                {"type": n.need_type.value, "intensity": n.intensity}
                for n in unfulfilled_needs
            ],
            "beliefs": [
                {"proposition": b.proposition, "confidence": b.confidence}
                for b in active_beliefs
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Stages internos
    # ------------------------------------------------------------------

    def _interpret(self, event: Event, raw_text: str) -> Interpretation:
        """Interpreta um evento. Para MVP: regras determinísticas.

        Em produção: LLM faria a interpretação.
        """
        interp = Interpretation(
            event_type=event.type,
            raw_text=raw_text,
            confidence=0.7,
        )

        # Interpretação determinística por tipo de evento
        if event.type == EventType.MIGUEL_SPOKE:
            interp.speaker = "miguel"
            interp.intent = "message"
            interp.sentiment = "neutral"
            interp.emotional_hint = {"affection": 0.05, "curiosity_level": 0.1}

        elif event.type == EventType.MIGUEL_LEFT:
            interp.speaker = "miguel"
            interp.intent = "departure"
            interp.sentiment = "negative"
            interp.emotional_hint = {"loneliness": 0.2, "sadness": 0.1}

        elif event.type == EventType.MIGUEL_RETURNED:
            interp.speaker = "miguel"
            interp.intent = "return"
            interp.sentiment = "positive"
            interp.emotional_hint = {"happiness": 0.2, "affection": 0.15}

        elif event.type == EventType.COMPLIMENT_RECEIVED:
            interp.intent = "compliment"
            interp.sentiment = "positive"
            interp.emotional_hint = {"happiness": 0.3, "affection": 0.2}

        elif event.type == EventType.INSULT_RECEIVED:
            interp.intent = "insult"
            interp.sentiment = "negative"
            interp.emotional_hint = {"anger": 0.3, "sadness": 0.2}

        elif event.type == EventType.NEW_PERSON_DETECTED:
            interp.intent = "new_person"
            interp.emotional_hint = {"curiosity_level": 0.4, "fear": 0.1}

        elif event.type == EventType.TASK_COMPLETED:
            interp.intent = "task_done"
            interp.sentiment = "positive"
            interp.emotional_hint = {"happiness": 0.15, "satisfaction": 0.2}

        elif event.type == EventType.TASK_FAILED:
            interp.intent = "task_failed"
            interp.sentiment = "negative"
            interp.emotional_hint = {"frustration": 0.3, "sadness": 0.1}

        elif event.type == EventType.LONELINESS_CHANGED:
            interp.intent = "internal_state"
            interp.emotional_hint = {"loneliness": 0.3}

        elif event.type == EventType.CURIOSITY_TRIGGERED:
            interp.intent = "internal_state"
            interp.emotional_hint = {"curiosity_level": 0.4}

        return interp

    def _appraise(self, interp: Interpretation) -> Appraisal:
        """Avalia impacto de uma interpretação na Mia.

        Combina: evento, contexto social, estado atual, personalidade.
        """
        emotion = self.affective.get_current()
        personality = self.identity.get_personality()

        # Relevância baseada no tipo de evento
        relevance = 0.5
        urgency = 0.0
        importance = 0.5

        if interp.speaker == "miguel":
            relevance = 0.8  # Miguel é sempre relevante
            importance = 0.7

        if interp.event_type in (EventType.INSULT_RECEIVED, EventType.TASK_FAILED):
            urgency = 0.7
            importance = 0.8

        if interp.event_type == EventType.MIGUEL_LEFT:
            urgency = 0.3
            importance = 0.6

        # Emotional deltas da interpretação
        emotion_deltas = dict(interp.emotional_hint)

        # Ajuste por personalidade
        traits = personality.traits.to_dict()
        if traits.get("empathy", 0.5) > 0.7:
            # Pessoa empática sente mais impacto de sentimentos alheios
            for key in emotion_deltas:
                emotion_deltas[key] *= 1.2

        if traits.get("neuroticism", 0.5) > 0.7:
            # Pessoa neurótica sente mais impacto negativo
            for key in emotion_deltas:
                if emotion_deltas[key] < 0:
                    emotion_deltas[key] *= 1.3

        # Need impacts
        need_impacts = {}
        if interp.event_type == EventType.MIGUEL_LEFT:
            need_impacts["social_interaction"] = 0.3
        elif interp.event_type == EventType.MIGUEL_RETURNED:
            need_impacts["social_interaction"] = -0.2  # reduz necessidade
        elif interp.event_type == EventType.CURIOSITY_TRIGGERED:
            need_impacts["novelty"] = -0.1

        # Belief updates
        belief_updates = []
        if interp.speaker == "miguel" and interp.sentiment == "positive":
            belief_updates.append({
                "proposition": "Miguel está comunicando positivamente",
                "confidence_delta": 0.05,
                "source": "observação direta",
            })
        elif interp.event_type == EventType.MIGUEL_LEFT:
            belief_updates.append({
                "proposition": "Miguel pode estar ocupado",
                "confidence_delta": 0.03,
                "source": "observação de ausência",
            })

        return Appraisal(
            relevance=relevance,
            urgency=urgency,
            importance=importance,
            emotion_deltas=emotion_deltas,
            need_impacts=need_impacts,
            belief_updates=belief_updates,
            reasoning=f"Evento {interp.event_type.value}: {interp.intent}, sentimento={interp.sentiment}",
        )

    def _decide_attention(
        self, interp: Interpretation, appraisal: Appraisal
    ) -> AttentionDecision:
        """Decisão de atenção baseada no appraisal."""
        evaluation = AttentionEvaluation(
            event_type=interp.event_type.value,
            event_id=None,
            relevance=appraisal.relevance,
            urgency=appraisal.urgency,
            importance=appraisal.importance,
            context={"sentiment": interp.sentiment, "speaker": interp.speaker},
            internal_state={"mood_valence": self.affective.get_current().mood.valence},
        )
        return self.attention.evaluate(evaluation)

    def _propose_state_transitions(
        self, interp: Interpretation, appraisal: Appraisal
    ) -> list[dict[str, Any]]:
        """Gera propostas de transição de estado."""
        proposals = []

        # 1. Proposta de mudança emocional
        if appraisal.emotion_deltas:
            emotion_proposal = self.affective.propose_emotion_change(
                appraisal.emotion_deltas,
                reason=appraisal.reasoning,
                source=interp.event_type.value,
            )
            proposals.append(emotion_proposal)

        # 2. Propostas de belief update
        for update in appraisal.belief_updates:
            beliefs = self.beliefs.list_active(limit=50)
            existing = None
            for b in beliefs:
                if b.proposition == update["proposition"]:
                    existing = b
                    break

            if existing:
                proposals.append({
                    "type": "belief_update",
                    "belief_id": existing.id,
                    "confidence_delta": update["confidence_delta"],
                    "evidence": update.get("source", ""),
                })
            else:
                # Nova crença
                new_belief = Belief(
                    proposition=update["proposition"],
                    confidence=0.5 + update.get("confidence_delta", 0),
                    source_evidence=update.get("source", ""),
                )
                self.beliefs.create(new_belief)
                proposals.append({
                    "type": "belief_update",
                    "belief_id": new_belief.id,
                    "action": "created",
                })

        # 3. Propostas de need fulfillment
        for need_type, impact in appraisal.need_impacts.items():
            if impact < 0:  # necessidade sendo satisfeita
                unfulfilled = self.needs_desires.list_unfulfilled_needs(limit=10)
                for need in unfulfilled:
                    if need.need_type.value == need_type:
                        proposals.append({
                            "type": "need_fulfillment",
                            "need_id": need.id,
                        })
                        break

        return proposals

    def _create_memory_candidate(
        self, event: Event, interp: Interpretation, appraisal: Appraisal
    ) -> dict[str, Any] | None:
        """Cria candidato de memória (não persiste diretamente — State Authority decide)."""
        if appraisal.importance < 0.3:
            return None  # Eventos triviais não viram memória

        content = f"[{interp.event_type.value}] "
        if interp.raw_text:
            content += interp.raw_text
        else:
            content += interp.intent or "evento interno"

        return {
            "content": content,
            "type": "experience",
            "source": interp.event_type.value,
            "importance": appraisal.importance,
            "confidence": interp.confidence,
            "scope": "personal",
            "person_id": "miguel" if interp.speaker == "miguel" else None,
            "emotional_context": appraisal.emotion_deltas,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _apply_belief_update(self, proposal: dict[str, Any]) -> None:
        """Aplica atualização de crença."""
        bid = proposal.get("belief_id")
        if not bid or proposal.get("action") == "created":
            return
        delta = proposal.get("confidence_delta", 0)
        evidence = proposal.get("evidence", "")
        if delta > 0:
            self.beliefs.increase_confidence(bid, delta, evidence)
        elif delta < 0:
            self.beliefs.decrease_confidence(bid, abs(delta), evidence)
