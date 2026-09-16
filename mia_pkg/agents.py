"""Subagents — Agent Registry, Orchestrator, Templates, Kill Switch.

Fase 13 do roadmap: Mia delega tarefas a subagentes com limites rígidos
(profundidade, custo, tempo, concorrência) via Resource Governor.
"""
from __future__ import annotations

import time
import uuid
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    KILLED = "killed"
    BLOCKED = "blocked"


class AgentRole(Enum):
    RESEARCH = "research"
    CODE = "code"
    SOCIAL = "social"
    GENERAL = "general"


@dataclass
class AgentConfig:
    """Configuração de um subagente."""
    role: AgentRole = AgentRole.GENERAL
    max_depth: int = 3
    max_cost: float = 10.0        # unidades abstratas de custo
    max_time_seconds: float = 1800.0  # 30 min
    capabilities: list[str] = field(default_factory=list)


@dataclass
class AgentTask:
    """Uma tarefa delegada a um subagente."""
    description: str
    parent_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: AgentConfig = field(default_factory=AgentConfig)
    created_at: float = field(default_factory=time.time)
    # Profundidade na árvore de delegação (0 = raiz). Computada pelo
    # Orchestrator na delegação via cadeia de parent_id.
    depth: int = 0


@dataclass
class AgentResult:
    """Resultado de um subagente."""
    task_id: str
    success: bool
    output: str = ""
    error: str = ""
    cost: float = 0.0
    duration: float = 0.0
    status: AgentStatus = AgentStatus.DONE


@dataclass
class SubAgent:
    """Um subagente registrado."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "agent"
    role: AgentRole = AgentRole.GENERAL
    config: AgentConfig = field(default_factory=AgentConfig)
    status: AgentStatus = AgentStatus.IDLE

    def run(self, task: AgentTask, governor, db: SQLiteConnection) -> AgentResult:
        """Executa uma tarefa (sobrescrito por templates)."""
        raise NotImplementedError

    def kill(self) -> None:
        self.status = AgentStatus.KILLED


# ======================================================================
# Agent Registry
# ======================================================================

class AgentRegistry:
    """Registro e lifecycle de subagentes."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._agents: dict[str, SubAgent] = {}

    def register(self, agent: SubAgent) -> SubAgent:
        """Registra um agente."""
        self._agents[agent.id] = agent
        return agent

    def get(self, agent_id: str) -> SubAgent | None:
        return self._agents.get(agent_id)

    def unregister(self, agent_id: str) -> bool:
        """Remove um agente (apenas se não estiver RUNNING)."""
        agent = self._agents.get(agent_id)
        if agent and agent.status != AgentStatus.RUNNING:
            del self._agents[agent_id]
            return True
        return False

    def list(self) -> list[SubAgent]:
        return list(self._agents.values())

    def list_by_role(self, role: AgentRole) -> list[SubAgent]:
        return [a for a in self._agents.values() if a.role == role]

    def find_for_capability(self, capability: str) -> SubAgent | None:
        """Encontra agente com capability específica."""
        for agent in self._agents.values():
            if capability in agent.config.capabilities:
                return agent
        return None

    def kill(self, agent_id: str) -> bool:
        """Kill switch por agente."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.kill()
        return True

    def kill_all(self) -> int:
        """Mata todos os agentes. Retorna quantos foram mortos."""
        count = 0
        for agent in self._agents.values():
            if agent.status == AgentStatus.RUNNING:
                agent.kill()
                count += 1
        return count


# ======================================================================
# Resource Governor (estende o da Fase 6 com verificação de limites)
# ======================================================================

class OrchestrationGovernor:
    """Verifica limites de profundidade, custo, tempo e concorrência."""

    def __init__(
        self,
        max_depth: int = 3,
        max_cost: float = 100.0,
        max_concurrency: int = 3,
        max_time_seconds: float = 3600.0,
    ) -> None:
        self.max_depth = max_depth
        self.max_cost = max_cost
        self.max_concurrency = max_concurrency
        self.max_time_seconds = max_time_seconds
        self._running: dict[str, AgentTask] = {}
        self._total_cost = 0.0

    def check_depth(self, depth: int, agent_config: AgentConfig) -> bool:
        """Limite de profundidade."""
        return depth <= min(self.max_depth, agent_config.max_depth)

    def check_cost(self, cost: float) -> bool:
        """Limite de custo acumulado."""
        return self._total_cost + cost <= self.max_cost

    def check_concurrency(self) -> bool:
        """Limite de tarefas concorrentes."""
        return len(self._running) < self.max_concurrency

    def check_time(self, started_at: float, agent_config: AgentConfig) -> bool:
        """Limite de tempo de execução."""
        elapsed = time.time() - started_at
        return elapsed <= min(self.max_time_seconds, agent_config.max_time_seconds)

    def acquire(self, task: AgentTask) -> bool:
        """Adquire slot de execução. False se exceder limites."""
        if not self.check_concurrency():
            return False
        self._running[task.id] = task
        return True

    def release(self, task: AgentTask, cost: float = 0.0) -> None:
        """Libera slot e registra custo."""
        self._running.pop(task.id, None)
        self._total_cost += cost

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def total_cost(self) -> float:
        return self._total_cost


# ======================================================================
# Orchestrator
# ======================================================================

class Orchestrator:
    """Roteia tarefas para agentes, respeitando limites do Governor."""

    def __init__(
        self,
        db: SQLiteConnection,
        registry: AgentRegistry,
        governor: OrchestrationGovernor | None = None,
    ) -> None:
        self._db = db
        self.registry = registry
        self.governor = governor or OrchestrationGovernor()
        # Rastreabilidade da hierarquia de tarefas: task_id → parent_task_id.
        # Raiz tem parent_id=None. Usado para calcular profundidade real
        # (não apenas "tem pai → 1").
        self._parents: dict[str, str | None] = {}

    def _compute_depth(self, task_id: str) -> int:
        """Profundidade determinística na árvore de delegação.

        root (parent=None) → 0
        filho → 1
        neto → 2
        ...

        Navega a cadeia de parent_id. Detecta CICLOS (parent_id que aponta
        para o próprio filho ou cadeia circular) — nesse caso trata como
        profundidade máxima (proteção contra loop infinito) e registra.
        """
        depth = 0
        seen: set[str] = set()
        current: str | None = task_id
        while current is not None:
            if current in seen:
                # ciclo detectado — não podemos navegar para sempre
                logger.warning("ciclo de parent_id detectado em %s", current)
                return depth
            seen.add(current)
            parent = self._parents.get(current, None)
            if parent is not None:
                depth += 1
            current = parent
        return depth

    def delegate(
        self,
        description: str,
        capability: str | None = None,
        role: AgentRole | None = None,
        parent_id: str | None = None,
    ) -> AgentResult:
        """Delega uma tarefa a um agente apropriado."""
        start = time.time()

        # 1. Escolhe agente
        agent: SubAgent | None = None
        if capability:
            candidate = self.registry.find_for_capability(capability)
            if candidate is None:
                return AgentResult(
                    task_id="", success=False,
                    error=f"nenhum agente com capability '{capability}'",
                    status=AgentStatus.FAILED,
                )
            if candidate.status == AgentStatus.KILLED:
                return AgentResult(
                    task_id="", success=False,
                    error="agente com capability morto (kill switch)",
                    status=AgentStatus.KILLED,
                )
            agent = candidate
        if agent is None and role:
            agents = [a for a in self.registry.list_by_role(role)
                      if a.status != AgentStatus.KILLED]
            agent = agents[0] if agents else None
        if agent is None:
            # qualquer agente idle
            idle = [a for a in self.registry.list()
                    if a.status == AgentStatus.IDLE and a.status != AgentStatus.KILLED]
            agent = idle[0] if idle else None
        if agent is None:
            return AgentResult(
                task_id="", success=False,
                error="nenhum agente disponível", status=AgentStatus.FAILED,
            )

        # 2. Verifica limites
        task = AgentTask(
            description=description,
            parent_id=parent_id,
            config=agent.config,
        )
        # registra hierarquia ANTES do cálculo de profundidade
        self._parents[task.id] = parent_id
        depth = self._compute_depth(task.id)
        task.depth = depth
        if not self.governor.check_depth(depth, agent.config):
            return AgentResult(
                task_id=task.id, success=False,
                error=f"profundidade {depth} excede limite", status=AgentStatus.BLOCKED,
            )
        if not self.governor.acquire(task):
            return AgentResult(
                task_id=task.id, success=False,
                error="limite de concorrência atingido", status=AgentStatus.BLOCKED,
            )
        agent.status = AgentStatus.RUNNING
        result: AgentResult | None = None
        try:
            # verifica tempo periodicamente
            result = agent.run(task, self.governor, self._db)
            if self.governor.check_time(start, agent.config):
                result.status = AgentStatus.DONE if result.success else AgentStatus.FAILED
            else:
                result.status = AgentStatus.BLOCKED
                result.error = "tempo excedido"
                result.success = False
        except Exception as e:
            result = AgentResult(
                task_id=task.id, success=False,
                error=str(e), status=AgentStatus.FAILED,
            )
        finally:
            if result is None:
                result = AgentResult(task.id, False, error="sem resultado", status=AgentStatus.FAILED)
            agent.status = AgentStatus.IDLE if agent.status != AgentStatus.KILLED else AgentStatus.KILLED
            self.governor.release(task, cost=result.cost)
            result.duration = time.time() - start

        return result


# ======================================================================
# Templates
# ======================================================================

class ResearchAgent(SubAgent):
    """Agente de pesquisa — busca info e retorna resumo.

    Markov: simula pesquisa (sem rede). Em produção, o handler de
    pesquisa seria plugado aqui (web_search, arxiv, etc).
    """

    def __init__(self, name: str = "research-1", search_fn: Callable[[str], str] | None = None) -> None:
        super().__init__(
            name=name,
            role=AgentRole.RESEARCH,
            config=AgentConfig(
                role=AgentRole.RESEARCH,
                capabilities=["search", "summarize"],
                max_depth=2,
                max_cost=5.0,
                max_time_seconds=600.0,
            ),
        )
        self._search_fn = search_fn

    def run(self, task: AgentTask, governor, db: SQLiteConnection) -> AgentResult:
        if self.status == AgentStatus.KILLED:
            return AgentResult(task.id, False, status=AgentStatus.KILLED, error="agente morto")
        try:
            if self._search_fn:
                output = self._search_fn(task.description)
            else:
                output = f"[research] tópico: {task.description} — (pesquisa simulada)"
            return AgentResult(task.id, True, output=output, cost=1.0)
        except Exception as e:
            return AgentResult(task.id, False, error=str(e), cost=0.5)


class CodeAgent(SubAgent):
    """Agente de código — gera/analisa código simples.

    Em produção, chamaria um LLM. Aqui retorna um stub seguro.
    """

    def __init__(self, name: str = "code-1") -> None:
        super().__init__(
            name=name,
            role=AgentRole.CODE,
            config=AgentConfig(
                role=AgentRole.CODE,
                capabilities=["write_code", "analyze_code"],
                max_depth=1,
                max_cost=8.0,
                max_time_seconds=1200.0,
            ),
        )

    def run(self, task: AgentTask, governor, db: SQLiteConnection) -> AgentResult:
        if self.status == AgentStatus.KILLED:
            return AgentResult(task.id, False, status=AgentStatus.KILLED, error="agente morto")
        return AgentResult(task.id, True, output=f"[code] stub seguro para: {task.description}", cost=2.0)


class SocialAgent(SubAgent):
    """Agente social — analisa interações sociais.

    Em produção, consultaria PeopleStore/RelationshipStore e geraria
    relatório social. Aqui retorna dados do DB.
    """

    def __init__(self, name: str = "social-1") -> None:
        super().__init__(
            name=name,
            role=AgentRole.SOCIAL,
            config=AgentConfig(
                role=AgentRole.SOCIAL,
                capabilities=["social_analysis", "relationship_insight"],
                max_depth=1,
                max_cost=3.0,
                max_time_seconds=300.0,
            ),
        )

    def run(self, task: AgentTask, governor, db: SQLiteConnection) -> AgentResult:
        if self.status == AgentStatus.KILLED:
            return AgentResult(task.id, False, status=AgentStatus.KILLED, error="agente morto")
        try:
            from mia_pkg.social import PeopleStore, RelationshipStore
            people = PeopleStore(db)
            rels = RelationshipStore(db)
            report_lines = []
            for p in people.list()[:5]:
                rel = rels.get(p.id)
                if rel:
                    report_lines.append(
                        f"{p.name}: trust={rel.trust:.2f} affinity={rel.affinity:.2f}"
                    )
                else:
                    report_lines.append(f"{p.name}: (sem relação ainda)")
            output = f"[social] {task.description}\n" + "\n".join(report_lines)
            return AgentResult(task.id, True, output=output, cost=0.5)
        except Exception as e:
            return AgentResult(task.id, False, error=str(e), cost=0.5)