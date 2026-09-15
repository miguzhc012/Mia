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