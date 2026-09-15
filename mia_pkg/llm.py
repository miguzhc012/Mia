"""LLM Abstraction — interface unificada para providers OpenAI-compatible.

Provider chain com fallback automático. Sem dependências externas.
Falha graciosa quando não há chave de API.
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ======================================================================
# Tipos
# ======================================================================

@dataclass
class Message:
    """Mensagem no formato padrão."""
    role: str  # "system", "user", "assistant", "tool"
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class TokenUsage:
    """Uso de tokens."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Resposta de um LLM provider."""
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    reasoning: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""


# ======================================================================
# Protocol / ABC
# ======================================================================

class LLMProvider(ABC):
    """Interface abstrata para qualquer provider OpenAI-compatible.

    Providers específicos implementam complete().
    """

    name: str = "provider"

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Envia prompt e retorna resposta."""
        ...

    def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Gera resposta incremental (yield fragments).

        Default: yield a resposta completa de uma vez (sem streaming real).
        Providers que suportam SSE sobrescrevem.
        """
        response = self.complete(messages, temperature, max_tokens)
        if response.content:
            yield response.content

    def is_available(self) -> bool:
        """Verifica se o provider tem credenciais disponíveis."""
        return True


# ======================================================================
# OpenAI-Compatible Provider (urllib simples)
# ======================================================================

class OpenAICompatProvider(LLMProvider):
    """Provider OpenAI-compatible usando urllib (sem httpx/requests).

    Falha graciosa quando não há chave de API.
    """

    def __init__(
        self,
        name: str = "openai",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key_env: str = "OPENAI_API_KEY",
        max_retries: int = 3,
        timeout: int = 60,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key_env = api_key_env
        self.max_retries = max_retries
        self.timeout = timeout
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Verifica se a chave de API existe no ambiente."""
        api_key = os.environ.get(self._api_key_env)
        return bool(api_key)

    def complete(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Chama a API OpenAI-compatible via urllib."""
        api_key = os.environ.get(self._api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Chave de API não encontrada em {self._api_key_env}. "
                f"Configure a variável de ambiente."
            )

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": m.role, "content": m.content or ""}
                for m in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        # Retry com exponential backoff + jitter
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                last_error = e
                code = e.code
                if code >= 500 or code == 429:
                    # erro transitório — retry com backoff
                    delay = (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Provider %s: HTTP %d (tentativa %d/%d), retry em %.1fs",
                        self.name, code, attempt + 1, self.max_retries, delay,
                    )
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"Erro HTTP {code}: {e.read().decode()}") from e
            except urllib.error.URLError as e:
                last_error = e
                delay = (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "Provider %s: conexão falhou (tentativa %d/%d), retry em %.1fs: %s",
                    self.name, attempt + 1, self.max_retries, delay, e.reason,
                )
                time.sleep(delay)
                continue
        else:
            raise RuntimeError(
                f"Provider {self.name} falhou após {self.max_retries} tentativas: {last_error}"
            ) from last_error

        choice = body.get("choices", [{}])[0]
        msg = choice.get("message", {})

        usage_data = body.get("usage", {})
        return LLMResponse(
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            usage=TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            ),
            provider=self.name,
            model=self.model,
        )


# ======================================================================
# Provider Chain (fallback)
# ======================================================================

class LLMProviderChain:
    """Chain de providers com fallback automático.

    Tenta cada provider em ordem; se falhar, tenta o próximo.
    """

    def __init__(self, providers: list[LLMProvider] | None = None, retries: int = 3) -> None:
        self._providers = providers or []
        self._retries = retries

    def add_provider(self, provider: LLMProvider) -> None:
        """Adiciona um provider à chain."""
        self._providers.append(provider)

    def complete(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Tenta complete em cada provider disponível, com retry.

        Retry com exponential backoff + jitter em erros transitórios.
        Se um provider falha definitivamente, tenta o próximo.

        Raises:
            RuntimeError: se nenhum provider disponível.
        """
        errors: list[str] = []
        for provider in self._providers:
            if not provider.is_available():
                logger.debug("Provider %s não disponível, pulando.", provider.name)
                continue
            # Tenta com retry (transitórios)
            for attempt in range(self._retries):
                try:
                    return provider.complete(messages, temperature, max_tokens)
                except Exception as e:
                    errors.append(f"{provider.name}: {e}")
                    is_transient = (
                        isinstance(e, urllib.error.HTTPError) and (e.code >= 500 or e.code == 429)
                    ) or isinstance(e, urllib.error.URLError)
                    if attempt < self._retries - 1 and is_transient:
                        delay = (2 ** attempt) + random.uniform(0, 0.5)
                        logger.warning(
                            "Provider %s falhou (tentativa %d/%d), retry em %.1fs: %s",
                            provider.name, attempt + 1, self._retries, delay, e,
                        )
                        time.sleep(delay)
                        continue
                    # Falha definitiva → tenta próximo provider
                    logger.warning("Provider %s falhou: %s", provider.name, e)
                    break

        raise RuntimeError(
            "Nenhum LLM provider disponível. "
            f"Erros: {'; '.join(errors) if errors else 'Nenhum provider configurado.'}"
        )

    def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Streaming com fallback entre providers.

        Yields fragmentos de texto. Se um provider falhar no meio,
        tenta o próximo (perde o progresso parcial).
        """
        errors: list[str] = []
        for provider in self._providers:
            if not provider.is_available():
                logger.debug("Provider %s não disponível, pulando.", provider.name)
                continue
            try:
                yield from provider.stream(messages, temperature, max_tokens)
                return
            except Exception as e:
                errors.append(f"{provider.name}: {e}")
                logger.warning("Provider %s falhou no stream: %s", provider.name, e)

        if errors:
            raise RuntimeError(
                "Nenhum LLM provider disponível para stream. "
                f"Erros: {'; '.join(errors)}"
            )
        raise RuntimeError("Nenhum LLM provider configurado.")
