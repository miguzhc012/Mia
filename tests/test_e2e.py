"""Testes E2E — Fase 16: integração completa de todos os componentes.

Fluxo completo: chat → cognição → emoção → memória → social → reflexão
→ autonomia → pesquisa → evolução.
"""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.llm import LLMProviderChain, LLMProvider, Message, LLMResponse, TokenUsage
from mia_pkg.chat import ChatSession
from mia_pkg.autonomy import Goal, GoalStore, GoalStatus
from mia_pkg.evolution import ParameterRegistry, RollbackManager, EvolutionEngine
from mia_pkg.monitoring import HealthMonitor


class StubProvider(LLMProvider):
    """Provider stub determinístico para E2E."""
    def __init__(self):
        self.name = "stub"
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        self.calls += 1
        text = "Entendi, Miguel! Vou guardar isso e pensar sobre."
        return LLMResponse(
            content=text,
            provider=self.name,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
        )


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestFullInteractionFlow:
    def test_chat_to_memory_to_social(self, db):
        """Chat → memória + relacionamento atualizado."""
        chat = ChatSession(db, LLMProviderChain([StubProvider()]))
        turn = chat.send("Oi Mia! Obrigado pela ajuda de ontem com o projeto")

        # memória criada
        memories = chat.memory.list_by_importance()
        assert len(memories) >= 1

        # relacionamento com miguel existe e trust aumentou (obrigado)
        person = chat.people.get_by_name("miguel")
        assert person is not None
        rel = chat.relationships.get(person.id)
        assert rel.trust >= 0.5

        # resposta veio do LLM
        assert turn.response_text

    def test_chat_consolidates_long_conversation(self, db):
        """Conversa longa → memórias consolidadas."""
        chat = ChatSession(db, LLMProviderChain([StubProvider()]))
        for i in range(10):
            chat.send(f"gosto muito de estudar python e automação {i}")
        # busca explícita por consolidadas (não top-10 por importância)
        consolidated = [
            m for m in chat.memory.search_by_content("[consolidado]")
            if m.is_consolidated
        ]
        assert len(consolidated) >= 1

    def test_goals_can_be_created_and_queried(self, db):
        """Autonomia: criar e listar objetivos."""
        store = GoalStore(db)
        goal = store.create(Goal(description="aprender Rust"))
        fetched = store.get(goal.id)
        assert fetched is not None
        assert fetched.status == GoalStatus.ACTIVE

    def test_evolution_proposal_applied_and_rolled_back(self, db):
        """Autoevolução: proposta aplicada + rollback."""
        reg = ParameterRegistry()
        reg.register("affective_engine", "decay_rate", 0.05, 0.0, 0.5)
        engine = EvolutionEngine(reg)
        prop = engine.propose_improvement("affective_engine", "decay_rate", +1, 0.1)
        from mia_pkg.evolution import EvolutionProposal
        proposal = EvolutionProposal(description="e2e", parameters=[prop])
        rm = RollbackManager(reg, health_check=lambda: False)
        # health check falha → rollback automático
        assert not rm.apply_with_canary(proposal, canary_seconds=0.0)
        assert reg.value("affective_engine", "decay_rate") == pytest.approx(0.05)

    def test_health_monitor_reports_system(self, db):
        """Monitoring: health report reflete estado."""
        monitor = HealthMonitor(db)
        report = monitor.health_check()
        assert report.db_ok
        assert report.tables["memory_objects"] >= 0
        status = monitor.component_status()
        assert status["db"] == "ok"

    def test_full_pipeline_latency_budget(self, db):
        """Performance: turn com stub resolve em <2s (critério Fase 16)."""
        import time
        chat = ChatSession(db, LLMProviderChain([StubProvider()]))
        start = time.monotonic()
        chat.send("teste de performance")
        elapsed = time.monotonic() - start
        assert elapsed < 2.0


class TestIdleProductive:
    def test_idle_research_uses_interests(self, db):
        """Modo idle: pesquisa tópicos de interesse e guarda conhecimento."""
        from mia_pkg.world import InterestTracker, WorldResearchAgent, IdleResearcher
        tracker = InterestTracker(db)
        tracker._bump("python", delta=0.7, source="chat")

        def fake_search(topic):
            return "python linguagem versatil para automacao e dados"

        agent = WorldResearchAgent(db, search_fn=fake_search, tracker=tracker)
        idle = IdleResearcher(db, agent, min_interest_weight=0.5)
        results = idle.run_idle_round(max_topics=3)

        assert len(results) >= 1
        # conhecimento persistido via KnowledgeStore (memória com tag)
        from mia_pkg.world import KnowledgeStore
        ks = KnowledgeStore(db)
        knowledge = ks.get_topic("python")
        assert len(knowledge) >= 1


class TestMultiAgentFlow:
    def test_orchestrated_research_delegation(self, db):
        """Fase 13: delegação a subagentes dentro do fluxo completo."""
        from mia_pkg.agents import (
            AgentRegistry, Orchestrator, ResearchAgent, CodeAgent, SocialAgent,
        )
        registry = AgentRegistry(db)
        registry.register(ResearchAgent("research-e2e"))
        registry.register(CodeAgent("code-e2e"))
        registry.register(SocialAgent("social-e2e"))
        orch = Orchestrator(db, registry)

        r1 = orch.delegate("pesquisar mercado de IA", capability="search")
        r2 = orch.delegate("revisar lógica", role=None)  # qualquer idle
        assert r1.success
        assert "research" in r1.output.lower()
        assert r2.success