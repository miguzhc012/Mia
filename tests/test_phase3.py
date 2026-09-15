"""Testes da Fase 1: Chat Session + CLI + integração LLM (Fase 1 do roadmap)."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType
from mia_pkg.llm import LLMProviderChain, Message, LLMResponse, TokenUsage, LLMProvider


# ======================================================================
# Mock LLM Provider
# ======================================================================

class MockProvider(LLMProvider):
    """Provider mock para testes — sempre responde."""
    def __init__(self, response_text: str = "Olá, Miguel! Como posso ajudar?") -> None:
        self.name = "mock"
        self.response_text = response_text
        self.calls: list[list[Message]] = []

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        self.calls.append(list(messages))
        return LLMResponse(
            content=self.response_text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="mock",
            model="mock-1",
        )


class FailingProvider(LLMProvider):
    """Provider que sempre falha."""
    def __init__(self) -> None:
        self.name = "failing"

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        raise RuntimeError("API down")


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# Chat Session
# ======================================================================

def test_chat_session_with_mock(db):
    """ChatSession com LLM mock retorna resposta do provider."""
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([MockProvider("Oi, tudo bem!")])
    session = ChatSession(db, chain)

    turn = session.send("oi mia")
    assert turn.response_text == "Oi, tudo bem!"
    assert turn.provider == "mock"
    assert turn.pipeline is not None
    assert len(session.history) == 2  # user + assistant


def test_chat_session_runs_cognitive_core(db):
    """ChatSession alimenta o Cognitive Core (memória candidata criada)."""
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([MockProvider("Interessante!")])
    session = ChatSession(db, chain)

    session.send("Gosto de programar em Python")
    mems = session.memory.list_by_importance(limit=5)
    assert len(mems) >= 1
    assert "Python" in mems[0].content or "programar" in mems[0].content


def test_chat_session_fallback_rules(db):
    """Sem LLM disponível, ChatSession usa regras."""
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([])  # sem providers
    session = ChatSession(db, chain)

    turn = session.send("oi mia")
    assert turn.provider == "rule-based"
    assert "Oi, Miguel!" in turn.response_text
    assert turn.pipeline is not None


def test_chat_session_fallback_provider_error(db):
    """Provider falha → usa regras (fallback gracioso)."""
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([FailingProvider()])
    session = ChatSession(db, chain)

    turn = session.send("tudo bem?")
    assert turn.provider == "rule-based"
    assert "estou" in turn.response_text.lower()


def test_chat_session_history_bounded(db):
    """Histórico é limitado ao max_history."""
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([MockProvider("ok")])
    session = ChatSession(db, chain, max_history=4)

    for i in range(10):
        session.send(f"mensagem {i}")
    assert len(session.history) <= 4


def test_reset_clears_history(db):
    """reset() limpa o histórico."""
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([MockProvider("ok")])
    session = ChatSession(db, chain)

    session.send("oi")
    session.reset()
    assert len(session.history) == 0


# ======================================================================
# Rule responder específico
# ======================================================================

def test_rule_responder_greetings(db):
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([])
    session = ChatSession(db, chain)

    resp, _ = session._rule_respond("oi mia!")
    assert "Oi, Miguel!" in resp


def test_rule_responder_identity(db):
    from mia_pkg.chat import ChatSession
    chain = LLMProviderChain([])
    session = ChatSession(db, chain)

    resp, _ = session._rule_respond("quem é você?")
    assert "Mia" in resp
    assert "valores" in resp


def test_rule_responder_memory_mentions(db):
    """Resposta a 'o que você lembra?' retorna memórias se existirem."""
    from mia_pkg.chat import ChatSession
    from mia_pkg.memory import MemoryObject, MemoryType
    chain = LLMProviderChain([])
    session = ChatSession(db, chain)

    session.memory.create(MemoryObject(
        content="Miguel gosta de café",
        type=MemoryType.preference,
        source="test",
        importance=0.9,
    ))
    resp, _ = session._rule_respond("o que você lembra?")
    assert "café" in resp


# ======================================================================
# LLM Chain (Fase 1 critérios)
# ======================================================================

def test_chain_fallback_to_second_provider(db):
    """Chain cai para segundo provider se o primeiro falhar."""
    from mia_pkg.llm import LLMProviderChain
    chain = LLMProviderChain([
        FailingProvider(),
        MockProvider("fallback ok"),
    ])
    resp = chain.complete([Message(role="user", content="oi")])
    assert resp.content == "fallback ok"
    assert resp.provider == "mock"


def test_chain_no_providers_raises(db):
    """Chain sem providers levanta RuntimeError."""
    from mia_pkg.llm import LLMProviderChain
    chain = LLMProviderChain([])
    with pytest.raises(RuntimeError):
        chain.complete([Message(role="user", content="oi")])


def test_chain_message_format():
    """Messages mantêm roles."""
    msgs = [
        Message(role="system", content="s"),
        Message(role="user", content="u"),
    ]
    assert msgs[0].role == "system"
    assert msgs[1].content == "u"


# ======================================================================
# CLI (usando dtach/pipe para não travar)
# ======================================================================

def test_cli_imports():
    """CLI importa sem erro."""
    import mia_pkg.cli  # noqa: F401


def test_cli_build_chain_empty_config():
    """build_llm_chain com config sem providers retorna chain vazia."""
    from mia_pkg.cli import build_llm_chain

    class FakeConfig:
        def get(self, key, default=None):
            return default

    chain = build_llm_chain(FakeConfig())
    assert len(chain._providers) == 0


def test_cli_format_turn():
    """format_turn produz texto legível."""
    from mia_pkg.chat import ChatTurn
    from mia_pkg.cli import format_turn
    turn = ChatTurn(user_text="oi", response_text="Oi!")
    out = format_turn(turn)
    assert "Oi!" in out
    assert "Mia" in out