"""Belief Revision — revisão automática de crenças com evidência.

Fase 7 critério: quando nova evidência contradiz crença, confiança diminui;
quando confiança < threshold, crença é marcada como obsoleta/rejeitada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mia_pkg.db import SQLiteConnection
from mia_pkg.beliefs import BeliefStore, Belief, BeliefStatus


@dataclass
class Evidence:
    """Uma evidência nova sobre uma crença."""
    proposition: str          # proposição observada
    supports: bool = True     # True=confirma, False=contradiz
    weight: float = 0.2       # impacto na confiança (0..1)
    source: str = ""          # origem da evidência


@dataclass
class BeliefRevisionResult:
    """Resultado do processamento de evidência."""
    belief_id: str
    proposition: str
    confidence_before: float
    confidence_after: float
    action: str = "no_change"  # increased | decreased | rejected | no_change
    reason: str = ""


class BeliefRevisionEngine:
    """Aplica evidências e gerencia revisão automática de crenças."""

    REJECT_THRESHOLD = 0.2    # confiança abaixo disso → rejeitada
    REVISE_THRESHOLD = 0.35   # confiança abaixo disso → marca como disputada

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._store = BeliefStore(db)

    def process_evidence(self, evidence: Evidence) -> list[BeliefRevisionResult]:
        """Processa evidência contra TODAS as crenças ativas similares.

        Retorna os resultados das crenças afetadas.
        """
        results: list[BeliefRevisionResult] = []
        active = self._store.list_active(limit=100)

        for belief in active:
            if not self._is_similar(belief.proposition, evidence.proposition):
                continue

            result = self._apply_to_belief(belief, evidence)
            if result.action != "no_change":
                results.append(result)

        return results

    def process_evidence_for(self, belief_id: str, evidence: Evidence) -> BeliefRevisionResult:
        """Processa evidência para uma crença específica."""
        belief = self._store.get(belief_id)
        if not belief:
            return BeliefRevisionResult(
                belief_id=belief_id, proposition=evidence.proposition,
                confidence_before=0, confidence_after=0,
                action="no_change", reason="crença não encontrada",
            )
        return self._apply_to_belief(belief, evidence)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _apply_to_belief(self, belief: Belief, evidence: Evidence) -> BeliefRevisionResult:
        """Aplica evidência e atualiza a crença."""
        before = belief.confidence

        if evidence.supports:
            new_conf = min(1.0, before + evidence.weight)
            self._store.increase_confidence(belief.id, evidence.weight, evidence.source)
            action = "increased"
            reason = f"evidência confirma: {evidence.proposition[:50]}"
        else:
            new_conf = max(0.0, before - evidence.weight)
            self._store.decrease_confidence(belief.id, evidence.weight, evidence.source)
            action = "decreased"
            reason = f"evidência contradiz: {evidence.proposition[:50]}"

            if new_conf < self.REJECT_THRESHOLD:
                self._store.reject(
                    belief.id,
                    reason=f"confiança {new_conf:.2f} < threshold {self.REJECT_THRESHOLD:.2f}",
                )
                action = "rejected"
            elif new_conf < self.REVISE_THRESHOLD:
                self._store._update_confidence(
                    belief, new_conf, f"disputada por evidência contrária"
                )
                action = "disputed"
                reason += f" (confiança {new_conf:.2f} — disputada)"

        return BeliefRevisionResult(
            belief_id=belief.id,
            proposition=belief.proposition,
            confidence_before=before,
            confidence_after=new_conf,
            action=action,
            reason=reason,
        )

    def _is_similar(self, proposition: str, evidence_prop: str) -> bool:
        """Verifica se a evidência é sobre a MESMA proposição.

        Heurística: palavras-chave comuns (excluindo stopwords).
        """
        p_words = {w for w in proposition.lower().split() if len(w) > 3}
        e_words = {w for w in evidence_prop.lower().split() if len(w) > 3}
        if not p_words or not e_words:
            return False
        overlap = p_words & e_words
        # pelo menos 40% das palavras do evidence estão na crença
        return len(overlap) / len(e_words) >= 0.4