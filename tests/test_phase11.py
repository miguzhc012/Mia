"""Testes da Fase 13: Subagentes, Orquestração, Resource Governor."""
import time
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.agents import (
    AgentRegistry, AgentStatus, AgentRole, AgentTask, AgentResult,
    Orchestrator, OrchestrationGovernor,
    ResearchAgent, CodeAgent, SocialAgent, SubAgent, AgentConfig,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
def registry(db):
    r = AgentRegistry(db)
    r.register(ResearchAgent("research-1"))
    r.register(CodeAgent("code-1"))
    r.register(SocialAgent("social-1"))
    return r


# ======================================================================
# Registry
# ======================================================================

class TestRegistry:
    def test_register_and_get(self, db):
        r = AgentRegistry(db)
        agent = ResearchAgent("r1")
        r.register(agent)
        assert r.get(agent.id) is agent

    def test_list_by_role(self, db):
        r = AgentRegistry(db)
        r.register(ResearchAgent("r1"))
        r.register(CodeAgent("c1"))
        assert len(r.list_by_role(AgentRole.RESEARCH)) == 1
        assert len(r.list_by_role(AgentRole.CODE)) == 1

    def test_find_for_capability(self, db):
        r = AgentRegistry(db)
        r.register(ResearchAgent("r1"))
        agent = r.find_for_capability("search")
        assert agent is not None
        assert agent.role == AgentRole.RESEARCH

    def test_unregister(self, db):
        r = AgentRegistry(db)
        agent = ResearchAgent("r1")
        r.register(agent)
        assert r.unregister(agent.id) is True
        assert r.get(agent.id) is None

    def test_kill_switch(self, db):
        r = AgentRegistry(db)
        agent = ResearchAgent("r1")
        r.register(agent)
        assert r.kill(agent.id) is True
        assert agent.status == AgentStatus.KILLED

    def test_kill_switch_unknown(self, db):
        r = AgentRegistry(db)
        assert r.kill("nao-existe") is False


# ======================================================================
# Orchestration Governor
# ======================================================================

class TestGovernor:
    def test_concurrency_limit(self):
        g = OrchestrationGovernor(max_concurrency=2)
        t1 = AgentTask("a"); t2 = AgentTask("b"); t3 = AgentTask("c")
        assert g.acquire(t1)
        assert g.acquire(t2)
        assert not g.acquire(t3)  # limite atingido
        g.release(t1)
        assert g.acquire(t3)  # slot liberado

    def test_depth_limit(self):
        g = OrchestrationGovernor(max_depth=3)
        cfg = AgentConfig(max_depth=3)
        assert g.check_depth(3, cfg)
        assert not g.check_depth(4, cfg)

    def test_cost_limit(self):
        g = OrchestrationGovernor(max_cost=10.0)
        g.release(AgentTask("x"), cost=8.0)
        assert g.check_cost(1.0)   # 8+1=9 <= 10
        assert not g.check_cost(3.0)  # 8+3=11 > 10

    def test_time_limit(self):
        g = OrchestrationGovernor(max_time_seconds=5.0)
        cfg = AgentConfig(max_time_seconds=5.0)
        assert g.check_time(time.time(), cfg)
        assert not g.check_time(time.time() - 10, cfg)

    def test_total_cost_tracked(self):
        g = OrchestrationGovernor(max_cost=100.0)
        g.release(AgentTask("x"), cost=2.5)
        g.release(AgentTask("y"), cost=3.5)
        assert g.total_cost == pytest.approx(6.0)


# ======================================================================
# Profundidade de subagentes (regressão H4)
#
# O bug antigo: `_compute_depth(parent_id)` retornava 0 se parent None
# e 1 caso contrário — neto/bisneto tinham a MESMA profundidade do filho,
# tornando o limite recursivo incorreto.
# ======================================================================

class TestAgentDepth:
    def _orch(self, db, registry):
        return Orchestrator(db, registry)

    def test_root_depth_zero(self, db, registry):
        """Tarefa raiz (sem parent) → profundidade 0."""
        orch = self._orch(db, registry)
        # delega raiz e inspeciona o task registrado
        result = orch.delegate("pesquisa raiz", capability="search")
        assert result.success
        task_id = result.task_id
        assert orch._compute_depth(task_id) == 0

    def test_child_depth_one(self, db, registry):
        """Filho (parent raiz) → profundidade 1."""
        orch = self._orch(db, registry)
        root = orch.delegate("tarefa raiz", capability="search")
        assert root.success
        child = orch.delegate(
            "tarefa filha", capability="search", parent_id=root.task_id
        )
        assert child.success
        assert orch._compute_depth(child.task_id) == 1

    def test_grandchild_depth_two(self, db, registry):
        """Neto → profundidade 2."""
        orch = self._orch(db, registry)
        root = orch.delegate("raiz", capability="search")
        child = orch.delegate("filho", capability="search", parent_id=root.task_id)
        grand = orch.delegate("neto", capability="search", parent_id=child.task_id)
        assert orch._compute_depth(grand.task_id) == 2

    def test_chain_depth_correct(self, db, registry):
        """Cadeia de 4 níveis → 0,1,2,3 (com agente de depth alto)."""
        from mia_pkg.agents import AgentConfig, AgentRole, SubAgent

        deep = SubAgent(
            name="deep-1", role=AgentRole.GENERAL,
            config=AgentConfig(
                role=AgentRole.GENERAL, max_depth=10, max_time_seconds=60,
                capabilities=["deep_chain"],
            ),
        )
        deep.run = lambda task, gov, db: AgentResult(task.id, True, output="ok")
        registry.register(deep)
        orch = Orchestrator(
            db, registry, OrchestrationGovernor(max_depth=10)
        )
        ids = []
        prev = None
        for i in range(4):
            r = orch.delegate(f"nível {i}", capability="deep_chain", parent_id=prev)
            assert r.success, r.error
            ids.append(r.task_id)
            prev = r.task_id
        for i, tid in enumerate(ids):
            assert orch._compute_depth(tid) == i, f"nível {i} deveria ter depth {i}"

    def test_above_max_depth_blocked(self, db, registry):
        """Task além do limite do governor → BLOCKED."""
        orch = Orchestrator(db, registry, OrchestrationGovernor(max_depth=2))
        root = orch.delegate("raiz", capability="search")
        child = orch.delegate("filho", capability="search", parent_id=root.task_id)
        assert child.success
        grand = orch.delegate("neto", capability="search", parent_id=child.task_id)
        assert grand.success  # depth 2 == max 2
        great = orch.delegate("bisneto", capability="search", parent_id=grand.task_id)
        # depth 3 > max 2 → blocked
        assert great.status == AgentStatus.BLOCKED
        assert "profundidade" in great.error

    def test_missing_parent_treated_as_root(self, db, registry):
        """Parent_id inexistente → não há como navegar → 0 (raiz)."""
        orch = self._orch(db, registry)
        assert orch._compute_depth("parent_id_inexistente") == 0

    def test_cycle_detected_no_infinite_loop(self, db, registry):
        """Ciclo na cadeia de parents → profundidade finita (sem loop)."""
        orch = self._orch(db, registry)
        a = orch.delegate("a", capability="search")
        b = orch.delegate("b", capability="search", parent_id=a.task_id)
        # cria ciclo: a aponta para b
        orch._parents[a.task_id] = b.task_id
        # navegação deve parar (profundidade finita)
        assert orch._compute_depth(b.task_id) >= 1

    def test_self_cycle(self, db, registry):
        """Task cujo parent é ela mesma → ciclo → profundidade finita."""
        orch = self._orch(db, registry)
        a = orch.delegate("a", capability="search")
        orch._parents[a.task_id] = a.task_id
        assert orch._compute_depth(a.task_id) >= 0

    def test_multiple_trees_independent(self, db, registry):
        """Duas árvores distintas não interferem entre si."""
        orch = self._orch(db, registry)
        r1 = orch.delegate("árvore1 raiz", capability="search")
        c1 = orch.delegate("árvore1 filho", capability="search", parent_id=r1.task_id)
        r2 = orch.delegate("árvore2 raiz", capability="search")
        assert orch._compute_depth(c1.task_id) == 1
        assert orch._compute_depth(r2.task_id) == 0
        assert orch._compute_depth(r1.task_id) == 0

    def test_parent_finished_still_counts(self, db, registry):
        """Parent já finalizado continua contando na cadeia (parents map retido)."""
        orch = self._orch(db, registry)
        root = orch.delegate("raiz", capability="search")
        child = orch.delegate("filho", capability="search", parent_id=root.task_id)
        # mesmo após o root terminar, a relação persiste no map
        assert orch._compute_depth(child.task_id) == 1


# ======================================================================
# Orchestrator
# ======================================================================

class TestOrchestrator:
    def test_delegate_research(self, db, registry):
        orch = Orchestrator(db, registry)
        result = orch.delegate("pesquisar sobre IA", capability="search")
        assert result.success
        assert "research" in result.output.lower()

    def test_delegate_by_role(self, db, registry):
        orch = Orchestrator(db, registry)
        result = orch.delegate("analisar código", role=AgentRole.CODE)
        assert result.success
        assert "code" in result.output.lower()

    def test_delegate_social_reads_db(self, db, registry):
        # seed pessoa para o agente social reportar
        from mia_pkg.social import PeopleStore, RelationshipStore
        PeopleStore(db).ensure("miguel")
        orch = Orchestrator(db, registry)
        result = orch.delegate("resumo social", role=AgentRole.SOCIAL)
        assert result.success
        assert "miguel" in result.output.lower()

    def test_no_agent_available(self, db):
        r = AgentRegistry(db)
        orch = Orchestrator(db, r)  # registry vazio
        result = orch.delegate("qualquer", capability="search")
        assert not result.success
        assert "nenhum" in result.error.lower()

    def test_concurrency_blocked(self, db, registry):
        orch = Orchestrator(db, registry, OrchestrationGovernor(max_concurrency=1))
        # primeira tarefa ocupa o slot
        r1 = orch.delegate("primeira", capability="search")
        # segunda deve ser bloqueada ou executada (slot liberado após fim)
        r2 = orch.delegate("segunda", capability="search")
        assert r1.success
        assert r2.success  # execução é síncrona; slot já liberado

    def test_task_cost_tracked(self, db, registry):
        orch = Orchestrator(db, registry)
        orch.delegate("pesquisa", capability="search")
        orch.delegate("pesquisa", capability="search")
        assert orch.governor.total_cost == pytest.approx(2.0)

    def test_agent_failure_propagates(self, db):
        class FailingAgent(SubAgent):
            def run(self, task, governor, db):
                raise RuntimeError("boom")
        r = AgentRegistry(db)
        r.register(FailingAgent("fail-1", role=AgentRole.GENERAL))
        orch = Orchestrator(db, r)
        result = orch.delegate("tarefa")
        assert not result.success
        assert "boom" in result.error


# ======================================================================
# Kill switch no meio da execução
# ======================================================================

class TestKillSwitch:
    def test_killed_agent_returns_killed(self, db, registry):
        r = registry
        agent = r.list_by_role(AgentRole.RESEARCH)[0]
        r.kill(agent.id)
        orch = Orchestrator(db, r)
        result = orch.delegate("pesquisa morta", capability="search")
        assert result.status == AgentStatus.KILLED or not result.success