"""Trust Boundary — identidade de componentes, kill switch, read-only mode.

Conceito (H18/H19/H22 do hardening):

  - ComponentRegistry: distingue "declared source" de "authenticated
    caller". Um componente NÃO pode simplesmente afirmar
    source="state_authority" e ganhar privilégios — ele precisa estar
    registrado e receber um token de componente (API interna).
  - KillSwitch: interrompe comportamento perigoso de verdade (não é
    documentação). Quando ativo, `is_blocked()` retorna True.
  - ReadOnlyMode: impede MUTAÇÕES no estado (não apenas alerta).
  - IntegrityChecker: verificação de conteúdo crítico.

Trust Boundary separa:
  - Mia adaptive system (pode propor, executar dentro de permissões)
  - system integrity boundary (secrets, permissions, core runtime,
    state authority, policy, budget, rollback, kill switch, deployment)

A Mia NÃO pode modificar mecanismos que protegem os próprios limites.
No MVP, code self-modification está BLOQUEADO.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ComponentKind(str, Enum):
    CORE = "core"            # dentro do trust boundary (autoridade)
    ADAPTIVE = "adaptive"    # Mia adaptive system (proposições apenas)
    EXTERNAL = "external"    # entrada não confiável


@dataclass
class Component:
    name: str
    kind: ComponentKind
    token: str = field(default_factory=lambda: secrets.token_hex(16))
    can_mutate_state: bool = False
    can_mutate_trust: bool = False   # NUNCA True para adaptive


class ComponentRegistry:
    """Registry de componentes registrados (identidade verificável).

    - `register()`: cria componente com token único.
    - `authenticate(name, token)`: valida identidade declarada.
    - `source_is_trusted(name, token)`: para decisões de autorização.

    Uma proposta com source="state_authority" mas SEM token válido é
    rejeitada: declared source ≠ authenticated caller.
    """

    def __init__(self) -> None:
        self._components: dict[str, Component] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        kind: ComponentKind = ComponentKind.ADAPTIVE,
        can_mutate_state: bool = False,
        can_mutate_trust: bool = False,
    ) -> Component:
        with self._lock:
            if name in self._components:
                raise ValueError(f"componente já registrado: {name}")
            cmp = Component(
                name=name,
                kind=kind,
                can_mutate_state=can_mutate_state,
                can_mutate_trust=can_mutate_trust,
            )
            self._components[name] = cmp
            return cmp

    def authenticate(self, name: str, token: str) -> Component | None:
        """Retorna o componente se (name, token) bater. None se inválido."""
        with self._lock:
            cmp = self._components.get(name)
            if cmp is None:
                return None
            return cmp if secrets.compare_digest(cmp.token, token) else None

    def source_is_trusted(self, name: str, token: str) -> bool:
        cmp = self.authenticate(name, token)
        return cmp is not None and cmp.kind == ComponentKind.CORE

    def can_mutate_state(self, name: str, token: str) -> bool:
        cmp = self.authenticate(name, token)
        return bool(cmp and cmp.can_mutate_state)

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._components)


class KillSwitch:
    """Interruptor de segurança REAL.

    Quando ativo:
      - `is_blocked()` → True (todos os consumidores consultam)
      - `block()` / `unblock()` — apenas via autoridade (owner token)

    Não é uma promessa em documentação: qualquer código que DEVE parar
    consulta `is_blocked()` antes de agir.
    """

    def __init__(self) -> None:
        self._blocked = False
        self._lock = threading.Lock()
        self._history: list[dict[str, Any]] = []

    def block(self, reason: str, by: str = "operator") -> None:
        with self._lock:
            self._blocked = True
            self._history.append({
                "action": "block",
                "reason": reason,
                "by": by,
                "at": datetime.now(timezone.utc).isoformat(),
            })

    def unblock(self, by: str = "operator") -> None:
        with self._lock:
            self._blocked = False
            self._history.append({
                "action": "unblock",
                "by": by,
                "at": datetime.now(timezone.utc).isoformat(),
            })

    def is_blocked(self) -> bool:
        with self._lock:
            return self._blocked

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)


class ReadOnlyMode:
    """Modo somente-leitura: impede MUTAÇÕES de verdade.

    - `enter()`: ativa
    - `exit()`: desativa
    - `assert_mutable()`: levanta ReadOnlyError se ativo — chamado por
      quem vai MUTAR estado (StateAuthority, MemoryStore, etc.)
    """

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.Lock()
        self._entered_at: str | None = None

    def enter(self, reason: str = "operator") -> None:
        with self._lock:
            self._active = True
            self._entered_at = datetime.now(timezone.utc).isoformat()
            self._reason = reason

    def exit(self) -> None:
        with self._lock:
            self._active = False
            self._entered_at = None

    def is_active(self) -> bool:
        with self._lock:
            return self._active

    def assert_mutable(self) -> None:
        """Levanta ReadOnlyError se o modo read-only está ativo."""
        if self.is_active():
            raise ReadOnlyError("sistema em modo somente-leitura")

    def info(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "since": self._entered_at,
                "reason": getattr(self, "_reason", None),
            }


class ReadOnlyError(Exception):
    """Levantada quando uma mutação tenta ocorrer em modo read-only."""


class IntegrityChecker:
    """Verifica integridade de conteúdo crítico (hash chain opcional).

    - `snapshot(content)`: registra hash do estado
    - `verify(content)`: compara com o último hash registrado
    - `corrupt()`: detecta divergência
    """

    def __init__(self) -> None:
        self._last_hash: str | None = None
        self._lock = threading.Lock()

    def snapshot(self, content: str) -> str:
        h = hashlib.sha256(content.encode()).hexdigest()
        with self._lock:
            self._last_hash = h
        return h

    def verify(self, content: str) -> bool:
        h = hashlib.sha256(content.encode()).hexdigest()
        with self._lock:
            return self._last_hash is not None and h == self._last_hash

    def corrupt(self) -> bool:
        with self._lock:
            self._last_hash = None
        return True