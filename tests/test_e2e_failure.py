"""Testes E2E de falha — componentes indisponíveis devem degradar com
elegância e SEMPRE avisar (nunca falhar silenciosamente -> comportamento
inesperado, nem simular sucesso).

Coverage H-série: falha de LLM, persistência, e circuito de eventos.
"""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventBus, EventRejectedError, EventType
from mia_pkg.llm import (
    LLMProviderChain, LLMProvider, LLMResponse, Message, TokenUsage,
)


class FailingProvider(LLMProvider):
    """Provider que descendente — LLM fora do ar deve ser detectado."""

    def __init__(self):
        self.name = "failing"
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        self.calls += 1
        raise ConnectionError("LLM fora do ar")


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestHonestFailure:
    def test_llm_failure_propagates_not_silent(self, db):
        """Falha do LLM NÃO é engolida: o caller sabe que falhou.

        O chain faz retry; ao esgotar, levanta RuntimeError com os erros
        acumulados (não retorna resposta falsa nem fica em silêncio).
        """
        chain = LLMProviderChain([FailingProvider()])
        with pytest.raises(RuntimeError) as excinfo:
            chain.complete([Message(role="user", content="oi")])
        # a causa raiz está visível na mensagem (não engolida)
        assert "ConnectionError" in str(excinfo.value) or "LLM fora do ar" in str(excinfo.value)

    def test_chain_fallback_uses_next_provider(self, db):
        """Chain com fallback: 1º provider falha, 2º responde (honesto)."""
        class OkProvider(LLMProvider):
            def __init__(self):
                self.name = "ok"
            def is_available(self):
                return True
            def complete(self, messages, temperature=0.7, max_tokens=4096):
                return LLMResponse(
                    content="resposta do fallback",
                    provider=self.name,
                    usage=TokenUsage(prompt_tokens=1, completion_tokens=1),
                )
        chain = LLMProviderChain([FailingProvider(), OkProvider()])
        resp = chain.complete([Message(role="user", content="oi")])
        assert resp.provider == "ok"
        assert resp.content == "resposta do fallback"

    def test_corrupt_db_fails_open_with_warning(self, tmp_path):
        """Banco corrompido: falha é REPORTADA (não falsifica sucesso)."""
        import sqlite3
        d = SQLiteConnection(str(tmp_path / "corrupt.db"))
        d.connect()
        d.init_schema()
        # corrompe: dropa tabela crítico sem aviso
        d.execute("DROP TABLE memory_objects")
        from mia_pkg.memory import MemoryStore
        store = MemoryStore(d)
        with pytest.raises(sqlite3.OperationalError):
            store.list_by_importance()

    def test_event_rejected_is_loud(self):
        """Evento rejeitado é exceção (loud), não log silencioso."""
        bus = EventBus()
        ev = Event()
        ev.type = "fake"  # type: ignore[assignment]
        with pytest.raises(EventRejectedError):
            bus.emit(ev)

    def test_event_bus_circuit_is_loud(self):
        """Circuito aberto é exceção para o caller (não falha muda)."""
        bus = EventBus(circuit_breaker_threshold=1)
        def boom(e):
            raise RuntimeError("x")
        bus.subscribe(EventType.MIGUEL_SPOKE, boom)
        bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="s"))  # 1º erro
        with pytest.raises(EventRejectedError):
            bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="s"))  # circuito