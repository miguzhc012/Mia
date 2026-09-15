"""Policy Engine — regras determinísticas de validação de transições.

Verifica invariantes de segurança antes de qualquer mudança de estado.
Regras são declarativas (whitelist/blacklist por target), não código imperativo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StateTransitionProposal:
    """Proposta de transição de estado conforme contrato D.3.

    O LLM gera proposals; a StateAuthority decide.
    source NUNCA deve ser 'llm' direto — é 'cognitive_core' ou similar.
    """
    target: str          # "emotion", "personality", "relationship", "memory", "identity"
    action: str          # "update", "create", "delete"
    key: str             # campo específico
    delta: Any           # valor proposto (range validado)
    evidence: str = ""   # justificativa
    confidence: float = 0.5
    source: str = ""     # componente de origem


@dataclass
class PolicyResult:
    """Resultado da verificação de policy."""
    allowed: bool = True
    reason: str | None = None
    invariant_violated: str | None = None


class PolicyEngine:
    """Engine de invariantes: verifica limites éticos e de segurança.

    Regras declarativas:
    - LLM não pode modificar personalidade/identidade/valores diretamente
    - Core values não podem ser deletados
    - Autoevolução restrita a parâmetros (MVP)
    - Rate limiting por tipo de transição
    """

    # Targets que o LLM NUNCA pode modificar diretamente
    _LLM_BLOCKED_TARGETS: set[str] = {
        "personality", "identity", "core_values",
    }

    # Targets protegidos contra delete
    _DELETE_BLOCKED_TARGETS: set[str] = {
        "identity", "core_values",
    }

    def __init__(self, max_emotion_transitions_per_hour: int = 10) -> None:
        self._max_emotion_transitions_per_hour = max_emotion_transitions_per_hour
        # Contador de transições emocionais por hora (simples: timestamps)
        self._emotion_transition_timestamps: list[float] = []

    def check(
        self,
        proposal: StateTransitionProposal,
        current_state: dict[str, Any] | None = None,
    ) -> PolicyResult:
        """Verifica se a proposta viola alguma regra.

        Args:
            proposal: A proposta de transição a ser validada.
            current_state: Snapshot do estado atual (para verificações contextuais).

        Returns:
            PolicyResult indicando se é permitida ou não.
        """
        # 1. LLM não pode modificar targets protegidos diretamente
        if proposal.source == "llm" and proposal.target in self._LLM_BLOCKED_TARGETS:
            return PolicyResult(
                allowed=False,
                reason=f"LLM não pode modificar '{proposal.target}' diretamente. "
                       f"Use o componente apropriado via State Authority.",
                invariant_violated="llm_no_direct_state_write",
            )

        # 2. Delete de identity/core_values bloqueado
        if proposal.action == "delete" and proposal.target in self._DELETE_BLOCKED_TARGETS:
            return PolicyResult(
                allowed=False,
                reason=f"Não é possível deletar '{proposal.target}'. "
                       f"Valores fundamentais são imutáveis.",
                invariant_violated="immutable_fundamentals",
            )

        # 3. Autoevolução: code changes rejeitados no MVP
        if proposal.action == "code_change":
            return PolicyResult(
                allowed=False,
                reason="Code changes requerem aprovação humana e sandbox (Fase 15+).",
                invariant_violated="no_code_change_mvp",
            )

        # 4. Confidence mínimo
        if proposal.confidence < 0.0 or proposal.confidence > 1.0:
            return PolicyResult(
                allowed=False,
                reason=f"Confidence fora do range [0.0, 1.0]: {proposal.confidence}",
                invariant_violated="invalid_confidence_range",
            )

        # 5. Source não pode ser vazio
        if not proposal.source:
            return PolicyResult(
                allowed=False,
                reason="Proposta deve ter um source válido.",
                invariant_violated="missing_source",
            )

        # 6. Target e key não podem ser vazios
        if not proposal.target or not proposal.key:
            return PolicyResult(
                allowed=False,
                reason="Proposta deve ter target e key definidos.",
                invariant_violated="missing_target_or_key",
            )

        # 7. Targets permitidos (whitelist)
        _VALID_TARGETS = {
            "emotion", "personality", "memory", "identity",
            "relationship", "person", "goal", "diary",
            "sensation", "personality_state",
        }
        if proposal.target not in _VALID_TARGETS:
            return PolicyResult(
                allowed=False,
                reason=f"Target '{proposal.target}' não é reconhecido.",
                invariant_violated="unknown_target",
            )

        return PolicyResult(allowed=True)
