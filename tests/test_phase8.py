"""Testes extras da Fase 1: retry com backoff e streaming."""
import urllib.error
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.llm import (
    LLMProviderChain, Message, LLMResponse, TokenUsage, LLMProvider,
)


class RetryProvider(LLMProvider):
    """Provider que falha N vezes antes de responder (simula 500/429)."""
    def __init__(self, fail_count: int = 2):
        self.name = "retry_provider"
        self.fail_count = fail_count
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        self.calls += 1
        if self.calls <= self.fail_count:
            # Simula HTTP 500 (transitório)
            raise urllib.error.HTTPError(
                "url", 500, "Internal Server Error", {}, None
            )
        return LLMResponse(
            content="ok após retries",
            usage=TokenUsage(total_tokens=10),
            provider=self.name,
            model="m",
        )


class FatalProvider(LLMProvider):
    """Provider que sempre falha com erro não-transitório."""
    def __init__(self):
        self.name = "fatal_provider"
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        self.calls += 1
        raise RuntimeError("erro fatal (não-transitório)")


class StreamProvider(LLMProvider):
    """Provider que faz streaming real (fragmentos)."""
    def __init__(self):
        self.name = "stream_provider"

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        return LLMResponse(content="resposta completa")

    def stream(self, messages, temperature=0.7, max_tokens=4096):
        for chunk in ["Olá, ", "Miguel! ", "Tudo ", "bem?"]:
            yield chunk


class StreamFailingProvider(LLMProvider):
    """Provider que falha no stream."""
    def __init__(self):
        self.name = "stream_failing"

    def is_available(self) -> bool:
        return True

    def complete(self, messages, temperature=0.7, max_tokens=4096) -> LLMResponse:
        raise RuntimeError("complete não usado")

    def stream(self, messages, temperature=0.7, max_tokens=4096):
        yield "parcial"
        raise RuntimeError("stream quebrou")


# ======================================================================
# Retry
# ======================================================================

class TestRetry:
    def test_retry_after_transient_failure(self):
        provider = RetryProvider(fail_count=2)
        assert provider.calls == 0
        chain = LLMProviderChain([provider])
        import mia_pkg.llm as llm_mod
        original_sleep = llm_mod.time.sleep
        llm_mod.time.sleep = lambda x: None  # não esperar nos testes
        try:
            resp = chain.complete([Message(role="user", content="oi")])
        finally:
            llm_mod.time.sleep = original_sleep
        assert resp.content == "ok após retries"
        assert provider.calls == 3  # 2 falhas + 1 sucesso

    def test_retry_exhausted_raises(self):
        provider = RetryProvider(fail_count=10)  # sempre falha
        chain = LLMProviderChain([provider])
        import mia_pkg.llm as llm_mod
        original_sleep = llm_mod.time.sleep
        llm_mod.time.sleep = lambda x: None
        try:
            with pytest.raises(RuntimeError):
                chain.complete([Message(role="user", content="oi")])
        finally:
            llm_mod.time.sleep = original_sleep
        assert provider.calls == 3  # max_retries=3

    def test_no_retry_on_fatal_error(self):
        """Erro não-transitório não faz retry — vai para o próximo provider."""
        provider = FatalProvider()
        ok_provider = StreamProvider()  # responde "resposta completa"
        chain = LLMProviderChain([provider, ok_provider])
        resp = chain.complete([Message(role="user", content="oi")])
        assert resp.content == "resposta completa"
        assert provider.calls == 1  # sem retry


# ======================================================================
# Streaming
# ======================================================================

class TestStreaming:
    def test_chain_stream_yields_fragments(self):
        chain = LLMProviderChain([StreamProvider()])
        chunks = list(chain.stream([Message(role="user", content="oi")]))
        assert chunks == ["Olá, ", "Miguel! ", "Tudo ", "bem?"]

    def test_chain_stream_fallback_on_failure(self):
        """Falha no stream → cai para próximo provider."""
        chain = LLMProviderChain([StreamFailingProvider(), StreamProvider()])
        chunks = list(chain.stream([Message(role="user", content="oi")]))
        assert "Olá, " in chunks  # veio do segundo provider

    def test_chain_stream_no_providers(self):
        chain = LLMProviderChain([])
        with pytest.raises(RuntimeError):
            list(chain.stream([Message(role="user", content="oi")]))

    def test_provider_default_stream_uses_complete(self):
        """Provider sem stream() sobrescrito usa complete() como fallback."""
        class BasicProvider(LLMProvider):
            name = "basic"
            def is_available(self): return True
            def complete(self, messages, temperature=0.7, max_tokens=4096):
                return LLMResponse(content="resposta inteira")

        provider = BasicProvider()
        chunks = list(provider.stream([Message(role="user", content="oi")]))
        assert chunks == ["resposta inteira"]