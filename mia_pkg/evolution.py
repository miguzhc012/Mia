"""Autoevolução — Evolution Engine, Parameter Evolver, Canary, Rollback.

Fase 15 do roadmap (MVP):
- Evolution Engine: gera propostas de melhoria (parâmetros)
- Parameter Evolver: ajusta weights dentro de ranges validados
- Canary Deployer: staging antes de produção
- Rollback Manager: snapshot antes + revert se health check falhar
- Code changes: REJEITADOS (MVP) — requer aprovação humana

Componentes imunes: core runtime, State Authority, Policy Engine.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection

# Componentes imunes à auto-modificação (Fase 15 critério 5)
IMMUNE_COMPONENTS = {
    "cognitive_core", "state_authority", "policy_engine",
    "db", "events", "config", "security",
}


@dataclass
class ParameterProposal:
    """Proposta de mudança de parâmetro."""
    component: str          # ex: "affective_engine"
    parameter: str          # ex: "decay_rate"
    current_value: float
    proposed_value: float
    min_value: float
    max_value: float
    rationale: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"  # pending | canary | active | rejected | rolled_back

    def validate(self) -> tuple[bool, str]:
        """Valida se a mudança é permitida (parâmetro, range, componente)."""
        if self.component in IMMUNE_COMPONENTS:
            return False, "componente imune a auto-modificação"
        if not (self.min_value <= self.proposed_value <= self.max_value):
            return False, "proposta fora do range permitido"
        if self.proposed_value == self.current_value:
            return False, "proposta sem mudança efetiva"
        return True, "ok"


@dataclass
class ParameterSnapshot:
    """Snapshot de parâmetro para rollback."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""
    parameter: str = ""
    value_before: float = 0.0
    value_after: float = 0.0
    timestamp: float = field(default_factory=time.time)
    active: bool = True


@dataclass
class EvolutionProposal:
    """Proposta completa de evolução (1+ parâmetros)."""
    description: str
    parameters: list[ParameterProposal] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending | canary | active | rejected | rolled_back
    code_change: bool = False  # MVP: sempre False (code changes rejeitados)


# ======================================================================
# Parameter Registry (valores correntes)
# ======================================================================

class ParameterRegistry:
    """Registra parâmetros mutáveis e seus ranges."""

    def __init__(self) -> None:
        self._params: dict[str, dict[str, dict]] = {}
        # key: (component, parameter) -> {value, min, max, description}

    def register(
        self, component: str, parameter: str,
        value: float, min_value: float, max_value: float,
        description: str = "",
    ) -> None:
        if component in IMMUNE_COMPONENTS:
            raise ValueError(f"componente {component} é imune a auto-modificação")
        self._params.setdefault(component, {})[parameter] = {
            "value": value, "min": min_value, "max": max_value,
            "description": description,
        }

    def get(self, component: str, parameter: str) -> dict | None:
        return self._params.get(component, {}).get(parameter)

    def value(self, component: str, parameter: str) -> float | None:
        p = self.get(component, parameter)
        return p["value"] if p else None

    def set(self, component: str, parameter: str, value: float) -> bool:
        """Define valor (dentro do range). Retorna False se inválido."""
        p = self.get(component, parameter)
        if not p:
            return False
        if not (p["min"] <= value <= p["max"]):
            return False
        p["value"] = value
        return True

    def list_all(self) -> list[dict]:
        out = []
        for comp, params in self._params.items():
            for name, p in params.items():
                out.append({
                    "component": comp, "parameter": name, **p,
                })
        return out


# ======================================================================
# Evolution Engine
# ======================================================================

class EvolutionEngine:
    """Gera propostas de evolução a partir de gaps observados."""

    def __init__(self, registry: ParameterRegistry) -> None:
        self._registry = registry

    def propose_improvement(
        self, component: str, parameter: str,
        direction: int,  # +1 aumentar, -1 diminuir
        step: float = 0.05,
        rationale: str = "",
    ) -> ParameterProposal:
        """Gera proposta de melhoria de um parâmetro."""
        p = self._registry.get(component, parameter)
        if not p:
            raise ValueError(f"parâmetro {component}.{parameter} não registrado")
        current = p["value"]
        proposed = max(p["min"], min(p["max"], current + direction * step))
        return ParameterProposal(
            component=component,
            parameter=parameter,
            current_value=current,
            proposed_value=proposed,
            min_value=p["min"],
            max_value=p["max"],
            rationale=rationale or f"ajuste {direction > 0 and 'para cima' or 'para baixo'} de {parameter}",
        )

    def propose_code_change(self, description: str) -> EvolutionProposal:
        """MVP: code changes são SEMPRE rejeitados (requer aprovação humana)."""
        proposal = EvolutionProposal(description=description, code_change=True)
        proposal.status = "rejected"
        return proposal


# ======================================================================
# Canary Deployer + Rollback Manager
# ======================================================================

class CanaryDeployer:
    """Staging antes de produção: aplica em canary, valida, promove."""

    def __init__(
        self,
        registry: ParameterRegistry,
        health_check: Callable[[], bool] | None = None,
        canary_seconds: float = 0.5,
    ) -> None:
        self._registry = registry
        self._health_check = health_check or (lambda: True)
        self._canary_seconds = canary_seconds
        self._canary_applied: list[ParameterProposal] = []

    def deploy_canary(self, proposal: EvolutionProposal) -> bool:
        """Aplica proposta em canary. False se alguma validação falhar."""
        if proposal.code_change:
            return False  # MVP: code change rejeitado

        for p in proposal.parameters:
            ok, _ = p.validate()
            if not ok:
                return False

        # aplica em canary (salva valores atuais)
        for p in proposal.parameters:
            current = self._registry.value(p.component, p.parameter)
            if current is not None:
                self._canary_applied.append(p)
                self._registry.set(p.component, p.parameter, p.proposed_value)
        return True

    def promote(self, proposal: EvolutionProposal) -> bool:
        """Promove canary para produção (mantém valores aplicados)."""
        if not self._canary_applied:
            return False
        for p in proposal.parameters:
            p.status = "active"
        self._canary_applied = []
        return True

    def rollback(self) -> None:
        """Reverte canary para valores originais."""
        for p in self._canary_applied:
            self._registry.set(p.component, p.parameter, p.current_value)
            p.status = "rolled_back"
        self._canary_applied = []

    def health_check_ok(self) -> bool:
        """Roda health check; se falhar, faz rollback automático."""
        if self._health_check():
            return True
        self.rollback()
        return False


class RollbackManager:
    """Snapshot antes + revert automático se health check falhar."""

    def __init__(
        self,
        registry: ParameterRegistry,
        health_check: Callable[[], bool] | None = None,
    ) -> None:
        self._registry = registry
        self._health_check = health_check or (lambda: True)
        self._snapshots: list[ParameterSnapshot] = []

    def snapshot(self, proposal: EvolutionProposal) -> list[ParameterSnapshot]:
        """Registra valores antes da aplicação."""
        snaps = []
        for p in proposal.parameters:
            current = self._registry.value(p.component, p.parameter)
            if current is not None:
                snap = ParameterSnapshot(
                    component=p.component, parameter=p.parameter,
                    value_before=current, value_after=p.proposed_value,
                )
                self._snapshots.append(snap)
                snaps.append(snap)
        return snaps

    def apply(self, proposal: EvolutionProposal) -> bool:
        """Aplica proposta (após snapshot). Valida tudo antes."""
        for p in proposal.parameters:
            ok, _ = p.validate()
            if not ok:
                return False
        for p in proposal.parameters:
            self._registry.set(p.component, p.parameter, p.proposed_value)
            p.status = "active"
        return True

    def rollback(self) -> int:
        """Reverte TODOS os snapshots ativos. Retorna quantos reverteu."""
        count = 0
        for snap in reversed(self._snapshots):
            if snap.active:
                self._registry.set(snap.component, snap.parameter, snap.value_before)
                snap.active = False
                count += 1
        return count

    def rollback_last(self) -> bool:
        """Reverte apenas o último snapshot ativo."""
        for snap in reversed(self._snapshots):
            if snap.active:
                self._registry.set(snap.component, snap.parameter, snap.value_before)
                snap.active = False
                return True
        return False

    def health_check_ok(self) -> bool:
        """Roda health check; falhou → rollback automático."""
        if self._health_check():
            return True
        self.rollback()
        return False

    def apply_with_canary(
        self, proposal: EvolutionProposal, canary_seconds: float = 0.5,
    ) -> bool:
        """Aplica com aprovação canary: snapshot, aplica, espera health check, promove."""
        self.snapshot(proposal)
        if self.apply(proposal):
            time.sleep(canary_seconds)
            if self.health_check_ok():
                return True
            self.rollback_last()
        return False