"""Testes unitários da fundação MIA.

Testa: EventBus, StateAuthority, MemoryStore, PolicyEngine, Config.
Sem dependência de rede — tudo in-memory/SQLite temporário.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from mia_pkg.config import Config, load_config
from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventBus, EventType
from mia_pkg.memory import MemoryObject, MemoryStore, MemoryType, MemoryScope
from mia_pkg.policy_engine import PolicyEngine, StateTransitionProposal
from mia_pkg.state_authority import StateAuthority, TransitionResult


# ======================================================================
# Helpers
# ======================================================================

def _temp_db() -> SQLiteConnection:
    """Cria um SQLite temporário para testes."""
    db = SQLiteConnection(":memory:")
    db.connect()
    db.init_schema()
    return db


def _make_proposal(
    target: str = "emotion",
    action: str = "update",
    key: str = "happiness",
    delta: float = 0.8,
    source: str = "cognitive_core",
    confidence: float = 0.7,
    evidence: str = "teste",
) -> StateTransitionProposal:
    return StateTransitionProposal(
        target=target,
        action=action,
        key=key,
        delta=delta,
        source=source,
        confidence=confidence,
        evidence=evidence,
    )


# ======================================================================
# EventBus
# ======================================================================

class TestEventBus(unittest.TestCase):
    """Testes do EventBus pub/sub."""

    def setUp(self) -> None:
        self.bus = EventBus()

    def test_subscribe_and_emit(self) -> None:
        """Handler recebe evento emitido."""
        received: list[Event] = []
        self.bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: received.append(e))

        event = Event(type=EventType.MIGUEL_SPOKE, source="cli", payload={"text": "olá"})
        self.bus.emit(event)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["text"], "olá")

    def test_filter_by_type(self) -> None:
        """Handler só recebe eventos do tipo que subscreveu."""
        received_spoke: list[Event] = []
        received_left: list[Event] = []

        self.bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: received_spoke.append(e))
        self.bus.subscribe(EventType.MIGUEL_LEFT, lambda e: received_left.append(e))

        self.bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="cli"))
        self.bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="cli"))
        self.bus.emit(Event(type=EventType.MIGUEL_LEFT, source="scheduler"))

        self.assertEqual(len(received_spoke), 2)
        self.assertEqual(len(received_left), 1)

    def test_unsubscribe(self) -> None:
        """Após unsubscribe, handler não recebe mais eventos."""
        received: list[Event] = []
        sub_id = self.bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: received.append(e))

        self.bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="cli"))
        self.assertEqual(len(received), 1)

        self.bus.unsubscribe(sub_id)
        self.bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="cli"))
        self.assertEqual(len(received), 1)  # não aumentou

    def test_multiple_handlers(self) -> None:
        """Múltiplos handlers recebem o mesmo evento."""
        count_a = [0]
        count_b = [0]
        self.bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: count_a.__setitem__(0, count_a[0] + 1))
        self.bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: count_b.__setitem__(0, count_b[0] + 1))

        self.bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="cli"))

        self.assertEqual(count_a[0], 1)
        self.assertEqual(count_b[0], 1)

    def test_invalid_event_type_rejected(self) -> None:
        """Evento com type inválido é rejeitado silenciosamente."""
        received: list[Event] = []
        self.bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: received.append(e))

        # Cria evento com type inválido (não é EventType)
        event = Event()
        event.type = "tipo_invalido"  # type: ignore[assignment]
        self.bus.emit(event)

        self.assertEqual(len(received), 0)

    def test_no_handlers_no_error(self) -> None:
        """Emit sem subscribers não levanta erro."""
        self.bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="cli"))

    def test_circuit_breaker(self) -> None:
        """Circuit breaker isola produtor após erros consecutivos.

        O circuit breaker é por produtor (source). Após threshold de erros,
        o produtor é isolado e nenhum handler recebe seus eventos.
        """
        bus = EventBus(circuit_breaker_threshold=2)
        received: list[Event] = []

        def bad_handler(event: Event) -> None:
            raise RuntimeError("falha simulada")

        bus.subscribe(EventType.MIGUEL_SPOKE, bad_handler)
        bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: received.append(e))

        # 2 emits → 2 erros no bad_handler + 2 entregas no good_handler
        bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="bad_producer"))
        bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="bad_producer"))
        self.assertEqual(len(received), 2)  # good handler recebeu nos primeiros 2

        # 3º emit → circuit breaker ativo, NENHUM handler chamado
        bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="bad_producer"))
        self.assertEqual(len(received), 2)  # não aumentou


# ======================================================================
# StateAuthority
# ======================================================================

class TestStateAuthority(unittest.TestCase):
    """Testes da StateAuthority — o componente mais crítico."""

    def setUp(self) -> None:
        self.db = _temp_db()
        self.policy = PolicyEngine()
        self.bus = EventBus()
        self.sa = StateAuthority(db=self.db, policy_engine=self.policy, event_bus=self.bus)

    def test_valid_transition_applied_and_audited(self) -> None:
        """Transição válida é aplicada e registrada no audit log."""
        proposal = _make_proposal(key="happiness", delta=0.8, source="cognitive_core")
        result = self.sa.propose(proposal)

        self.assertTrue(result.applied)
        self.assertIsNotNone(result.transition_id)
        self.assertTrue(result.validation.valid)
        self.assertTrue(result.policy.allowed)

        # Verifica audit log
        rows = self.db.fetchall("SELECT * FROM state_transitions_audit")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target"], "emotion")
        self.assertEqual(rows[0]["key"], "happiness")

    def test_invalid_transition_blocked(self) -> None:
        """Transição que viole range é bloqueada."""
        proposal = _make_proposal(key="happiness", delta=5.0, source="cognitive_core")
        result = self.sa.propose(proposal)

        self.assertFalse(result.applied)
        self.assertFalse(result.validation.valid)
        self.assertIn("fora do range", result.validation.errors[0])

    def test_llm_cannot_call_apply_directly(self) -> None:
        """LLM não pode escrever estado diretamente — enforcement físico."""
        proposal = _make_proposal(
            key="happiness", delta=0.9, source="llm"
        )
        result = self.sa.propose(proposal)

        # LLM com target protegido é bloqueado
        proposal_protected = _make_proposal(
            target="personality", key="curiosity", delta=0.9, source="llm"
        )
        result2 = self.sa.propose(proposal_protected)
        self.assertFalse(result2.applied)
        self.assertFalse(result2.policy.allowed)
        self.assertIn("llm_no_direct_state_write", result2.policy.invariant_violated)

    def test_audit_hash_chain(self) -> None:
        """Cada registro de auditoria tem hash do anterior."""
        for i in range(3):
            proposal = _make_proposal(
                key="happiness", delta=0.5 + i * 0.1, source="cognitive_core"
            )
            self.sa.propose(proposal)

        rows = self.db.fetchall(
            "SELECT hash_prev FROM state_transitions_audit ORDER BY timestamp"
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["hash_prev"], "0" * 64)  # primeiro
        self.assertNotEqual(rows[1]["hash_prev"], "0" * 64)  # aponta pro anterior


# ======================================================================
# MemoryStore
# ======================================================================

class TestMemoryStore(unittest.TestCase):
    """Testes de CRUD e importance scoring."""

    def setUp(self) -> None:
        self.db = _temp_db()
        self.store = MemoryStore(self.db)

    def test_create_and_get(self) -> None:
        """MemoryObject é criado e recuperado."""
        obj = MemoryObject(
            content="Miguel gosta de café",
            type=MemoryType.preference,
            source="conversation",
            importance=0.8,
            tags=["café", "preferência"],
        )
        self.store.create(obj)
        retrieved = self.store.get(obj.id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.content, "Miguel gosta de café")
        self.assertEqual(retrieved.type, MemoryType.preference)
        self.assertEqual(retrieved.importance, 0.8)
        self.assertEqual(retrieved.tags, ["café", "preferência"])

    def test_update_importance(self) -> None:
        """Importance pode ser atualizada."""
        obj = MemoryObject(content="fato importante", type=MemoryType.fact)
        self.store.create(obj)

        self.assertTrue(self.store.update_importance(obj.id, 0.95))
        retrieved = self.store.get(obj.id)
        self.assertEqual(retrieved.importance, 0.95)

    def test_importance_range_validation(self) -> None:
        """Importance fora de [0.0, 1.0] é rejeitada."""
        obj = MemoryObject(content="teste", type=MemoryType.fact)
        self.store.create(obj)

        self.assertFalse(self.store.update_importance(obj.id, 1.5))
        self.assertFalse(self.store.update_importance(obj.id, -0.1))

    def test_list_by_importance(self) -> None:
        """Memórias listadas por importância decrescente."""
        for i, imp in enumerate([0.3, 0.9, 0.6]):
            self.store.create(MemoryObject(
                content=f"memória {i}", type=MemoryType.experience, importance=imp
            ))

        result = self.store.list_by_importance(limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].importance, 0.9)
        self.assertEqual(result[1].importance, 0.6)

    def test_search_by_content(self) -> None:
        """Busca por keyword retorna memórias relevantes."""
        self.store.create(MemoryObject(content="Miguel adora café", type=MemoryType.preference))
        self.store.create(MemoryObject(content="Dia chuvoso", type=MemoryType.experience))

        result = self.store.search_by_content("café")
        self.assertEqual(len(result), 1)
        self.assertIn("café", result[0].content)

    def test_delete(self) -> None:
        """Delete remove a memória."""
        obj = MemoryObject(content="para deletar", type=MemoryType.fact)
        self.store.create(obj)
        self.store.delete(obj.id)
        self.assertIsNone(self.store.get(obj.id))

    def test_count(self) -> None:
        """Count retorna o total correto."""
        self.assertEqual(self.store.count(), 0)
        self.store.create(MemoryObject(content="a", type=MemoryType.fact))
        self.store.create(MemoryObject(content="b", type=MemoryType.fact))
        self.assertEqual(self.store.count(), 2)


# ======================================================================
# PolicyEngine
# ======================================================================

class TestPolicyEngine(unittest.TestCase):
    """Testes das regras determinísticas da Policy Engine."""

    def setUp(self) -> None:
        self.engine = PolicyEngine()

    def test_llm_blocked_from_personality(self) -> None:
        """LLM não pode modificar personalidade diretamente."""
        proposal = _make_proposal(target="personality", source="llm")
        result = self.engine.check(proposal)
        self.assertFalse(result.allowed)
        self.assertIn("llm_no_direct_state_write", result.invariant_violated)

    def test_llm_blocked_from_identity(self) -> None:
        """LLM não pode modificar identidade diretamente."""
        proposal = _make_proposal(target="identity", source="llm")
        result = self.engine.check(proposal)
        self.assertFalse(result.allowed)

    def test_delete_identity_blocked(self) -> None:
        """Delete de identity é sempre bloqueado."""
        proposal = _make_proposal(target="identity", action="delete", source="cognitive_core")
        result = self.engine.check(proposal)
        self.assertFalse(result.allowed)
        self.assertIn("immutable_fundamentals", result.invariant_violated)

    def test_valid_proposal_allowed(self) -> None:
        """Proposta válida de componente legítimo é permitida."""
        proposal = _make_proposal(target="emotion", source="cognitive_core")
        result = self.engine.check(proposal)
        self.assertTrue(result.allowed)
        self.assertIsNone(result.invariant_violated)

    def test_code_change_rejected(self) -> None:
        """Code changes são rejeitados no MVP."""
        proposal = _make_proposal(action="code_change", source="evolution")
        result = self.engine.check(proposal)
        self.assertFalse(result.allowed)
        self.assertIn("no_code_change_mvp", result.invariant_violated)

    def test_empty_source_rejected(self) -> None:
        """Source vazio é rejeitado."""
        proposal = _make_proposal(source="")
        result = self.engine.check(proposal)
        self.assertFalse(result.allowed)
        self.assertIn("missing_source", result.invariant_violated)

    def test_unknown_target_rejected(self) -> None:
        """Target desconhecido é rejeitado."""
        proposal = _make_proposal(target="unknown_thing", source="cognitive_core")
        result = self.engine.check(proposal)
        self.assertFalse(result.allowed)
        self.assertIn("unknown_target", result.invariant_violated)

    def test_emotion_allowed_for_llm(self) -> None:
        """LLM pode propor mudanças emocionais (via cognitive_core)."""
        proposal = _make_proposal(target="emotion", source="cognitive_core")
        result = self.engine.check(proposal)
        self.assertTrue(result.allowed)


# ======================================================================
# Config
# ======================================================================

class TestConfig(unittest.TestCase):
    """Testes de carregamento e defaults da configuração."""

    def test_defaults(self) -> None:
        """Config tem defaults corretos."""
        config = Config()
        self.assertEqual(config.get("system.name"), "Mia")
        self.assertEqual(config.get("system.version"), "0.1.0")
        self.assertEqual(config.get("llm.temperature"), 0.7)
        self.assertEqual(config.get("memory.max_objects"), 10000)

    def test_dotted_access(self) -> None:
        """Acesso pontilhado funciona."""
        config = Config({"llm": {"model": "gpt-4o"}})
        self.assertEqual(config.get("llm.model"), "gpt-4o")

    def test_missing_key_returns_default(self) -> None:
        """Chave inexistente retorna default."""
        config = Config()
        self.assertIsNone(config.get("nonexistent"))
        self.assertEqual(config.get("nonexistent", "fallback"), "fallback")

    def test_load_from_json_file(self) -> None:
        """Carrega config de arquivo JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps({"llm": {"model": "custom"}}))

            config = load_config(config_dir=tmpdir)
            self.assertEqual(config.get("llm.model"), "custom")
            # Defaults preservados
            self.assertEqual(config.get("llm.temperature"), 0.7)

    def test_data_property(self) -> None:
        """Property data retorna dados sem expor secrets."""
        config = Config({"llm": {"api_key_env": "MY_KEY"}})
        data = config.data
        self.assertEqual(data["llm"]["api_key_env"], "MY_KEY")


# ======================================================================
# Integration: StateAuthority + EventBus
# ======================================================================

class TestIntegration(unittest.TestCase):
    """Testes de integração entre componentes."""

    def test_propose_emits_event(self) -> None:
        """Proposta válida emite evento no Event Bus."""
        db = _temp_db()
        bus = EventBus()
        sa = StateAuthority(db=db, policy_engine=PolicyEngine(), event_bus=bus)

        received: list[Event] = []
        bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: received.append(e))

        proposal = _make_proposal(key="happiness", delta=0.7)
        result = sa.propose(proposal)

        self.assertTrue(result.applied)
        self.assertGreater(len(received), 0)

    def test_policy_blocks_before_apply(self) -> None:
        """Policy Engine bloqueia antes da aplicação — estado não muda."""
        db = _temp_db()
        bus = EventBus()
        sa = StateAuthority(db=db, policy_engine=PolicyEngine(), event_bus=bus)

        proposal = _make_proposal(target="personality", key="curiosity", delta=0.9, source="llm")
        result = sa.propose(proposal)

        self.assertFalse(result.applied)
        # Audit log vazio
        rows = db.fetchall("SELECT * FROM state_transitions_audit")
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
