"""Security Hardening — Secrets redaction, Rate Limiting, Integrity Checker.

Fase 8 do roadmap:
- Secrets: redação automática em logs (***)
- Rate limiting configurável por tipo de transição
- Alertas: taxa anormal → modo read-only + alerta
- Integrity Checker: hash chain verification periódica
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection

logger = logging.getLogger(__name__)

# ======================================================================
# Secrets Redactor
# ======================================================================

class SecretsRedactor:
    """Redige segredos em strings/logs: APIs keys, tokens, senhas."""

    _PATTERNS: list[tuple[str, re.Pattern]] = [
        ("openai_key", re.compile(r"sk-[A-Za-z0-9_-]{16,}")),
        ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
        ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
        ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE)),
        ("authorization_header", re.compile(r"Authorization\s*:\s*(?!\[[a-z_]+:\*\*\*\])\S+", re.IGNORECASE)),
        ("basic_auth", re.compile(r"Basic\s+[A-Za-z0-9+/=]{16,}", re.IGNORECASE)),
        ("password", re.compile(r"(?:password|senha|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{4,}", re.IGNORECASE)),
        ("api_key", re.compile(r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?[^\s'\"]{8,}", re.IGNORECASE)),
        ("token", re.compile(r"(?:token|access[_-]?token|auth[_-]?token)\s*[=:]\s*['\"]?[^\s'\"]{8,}", re.IGNORECASE)),
        ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
        ("generic_uuid_secret", re.compile(r"(?:secret|chave|key)\s*[=:]\s*['\"]?[0-9a-fA-F-]{20,}", re.IGNORECASE)),
    ]

    def __init__(self, patterns: list[dict] | None = None) -> None:
        """patterns: lista opcional de {name, regex} para customização."""
        self._patterns = list(self._PATTERNS)
        for p in patterns or []:
            self._patterns.append((p.get("name", "custom"), re.compile(p.get("regex", ""))))

    def redact(self, text: str) -> str:
        """Substitui segredos por '***'."""
        if not text:
            return text
        result = text
        for name, pattern in self._patterns:
            result = pattern.sub(f"[{name}:***]", result)
        return result

    def contains_secret(self, text: str) -> bool:
        """True se o texto contém algum segredo."""
        return any(p.search(text) for _, p in self._patterns)


# ======================================================================
# Rate Limiter
# ======================================================================

@dataclass
class RateLimitConfig:
    """Configuração de limite para uma categoria."""
    category: str
    max_events: int = 100
    window_seconds: int = 3600  # 1h
    alert_threshold: float = 0.8  # 80% do limite → alerta


class RateLimiter:
    """Limita eventos por categoria em janela deslizante.

    Usado para: transições de estado, chamadas LLM, ações autônomas.
    """

    def __init__(self, configs: list[RateLimitConfig] | None = None) -> None:
        self._configs: dict[str, RateLimitConfig] = {
            c.category: c for c in (configs or [
                RateLimitConfig("state_transition", max_events=1000, window_seconds=3600),
                RateLimitConfig("llm_call", max_events=300, window_seconds=3600),
                RateLimitConfig("autonomous_action", max_events=50, window_seconds=3600),
                RateLimitConfig("chat_message", max_events=200, window_seconds=3600),
            ])
        }
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._alerts: list[dict[str, Any]] = []
        self._read_only = False

    def check(self, category: str) -> bool:
        """Registra um evento; True se permitido, False se limite excedido."""
        config = self._configs.get(category)
        if config is None:
            return True  # categoria desconhecida não é limitada
        now = time.monotonic()

        with self._lock:
            events = self._events.setdefault(category, [])
            # remove eventos fora da janela
            cutoff = now - config.window_seconds
            events[:] = [t for t in events if t > cutoff]

            if len(events) >= config.max_events:
                return False
            events.append(now)

            ratio = len(events) / config.max_events
            if ratio >= config.alert_threshold and not self._read_only:
                self._alerts.append({
                    "category": category,
                    "ratio": round(ratio, 3),
                    "count": len(events),
                    "max": config.max_events,
                    "at": datetime.now(timezone.utc).isoformat(),
                })
                if ratio >= 1.0:
                    self._read_only = True
                    logger.warning("Rate limit excedido em %s — modo read-only", category)
            return True

    def status(self) -> dict[str, Any]:
        """Estado atual dos limites (para monitoramento)."""
        now = time.monotonic()
        with self._lock:
            status = {}
            for category, config in self._configs.items():
                events = [t for t in self._events.get(category, []) if t > now - config.window_seconds]
                status[category] = {
                    "count": len(events),
                    "max": config.max_events,
                    "ratio": round(len(events) / config.max_events, 3) if config.max_events else 0,
                }
            return {
                "limits": status,
                "read_only": self._read_only,
                "alerts": list(self._alerts),
            }


# ======================================================================
# Integrity Checker
# ======================================================================

class IntegrityChecker:
    """Verifica a hash chain do audit log periodicamente."""

    def __init__(self, db: SQLiteConnection, interval_seconds: int = 3600) -> None:
        self._db = db
        self._interval = interval_seconds
        self._last_check: float = 0.0
        self._last_result: tuple[bool, int, list[str]] = (True, 0, [])

    def check_now(self) -> tuple[bool, int, list[str]]:
        """Verifica agora a integridade. Retorna (ok, registros, erros)."""
        rows = self._db.fetchall(
            "SELECT id, target, key, before_snapshot, after_snapshot, hash, hash_prev "
            "FROM state_transitions_audit ORDER BY rowid ASC"
        )
        prev = "0" * 64
        errors: list[str] = []
        count = 0
        for row in rows:
            count += 1
            payload = (
                f"{row['id']}:{row['target']}:{row['key']}:"
                f"{row['before_snapshot']}:{row['after_snapshot']}:{row['hash_prev']}"
            )
            calc = hashlib.sha256(payload.encode()).hexdigest()
            if row["hash_prev"] != prev:
                errors.append(f"Registro hash_prev não bate (índice {count})")
            if row["hash"] != calc:
                errors.append(f"Registro hash corrente não confere (índice {count})")
            prev = row["hash"]
        self._last_result = (len(errors) == 0, count, errors)
        self._last_check = time.monotonic()
        return self._last_result

    def check_due(self) -> bool:
        """True se a verificação periódica é devida."""
        return time.monotonic() - self._last_check >= self._interval

    def verify(self) -> tuple[bool, int, list[str]]:
        """Verifica se devido; senão retorna último resultado."""
        if self.check_due():
            return self.check_now()
        return self._last_result

    @property
    def last_result(self) -> tuple[bool, int, list[str]]:
        return self._last_result


# ======================================================================
# Sandbox (preparação para autoevolução)
# ======================================================================

class Sandbox:
    """Contrato de sandbox para ações autônomas (Fase 8 preparação).

    Ações que requerem sandbox devem implementar o protocolo:
    propose() -> validate() -> approve() -> execute(no sandbox)
    """

    ALLOWED_MODULES: frozenset[str] = frozenset({
        "math", "json", "datetime", "uuid", "sqlite3", "random",
        "re", "string", "collections", "itertools", "statistics",
    })

    BLOCKED_KEYWORDS: tuple[str, ...] = (
        "os.system", "subprocess", "socket", "open(", "eval(", "exec(",
        "__import__", "shutil.rmtree", "os.remove", "pickle.loads",
    )

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db

    def validate_code(self, code: str) -> tuple[bool, list[str]]:
        """Valida se código é seguro para executar no sandbox."""
        errors: list[str] = []
        for kw in self.BLOCKED_KEYWORDS:
            if kw in code:
                errors.append(f"bloqueado: '{kw}'")
        return (len(errors) == 0, errors)

    def validate_imports(self, code: str) -> tuple[bool, list[str]]:
        """Valida imports usados no código."""
        errors: list[str] = []
        for line in code.splitlines():
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                module = line.split()[1].split(".")[0]
                if module not in self.ALLOWED_MODULES:
                    errors.append(f"módulo não permitido: {module}")
        return (len(errors) == 0, errors)

    def audit_action(self, action: str, code: str, allowed: bool, reason: str) -> None:
        """Registra ação no log de auditoria de sandbox."""
        self._db.execute(
            """INSERT INTO sandbox_actions
               (id, action, code_hash, allowed, reason, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(secrets.token_hex(16)),
                action,
                hashlib.sha256(code.encode()).hexdigest(),
                allowed,
                reason,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._db.commit()


# ======================================================================
# Enhanced Audit Log (alerta de taxa anormal)
# ======================================================================

class AuditMonitor:
    """Monitora audit log e gera alertas em padrões anormais."""

    def __init__(self, db: SQLiteConnection, rate_limiter: RateLimiter | None = None) -> None:
        self._db = db
        self._limiter = rate_limiter or RateLimiter()
        self._baseline: tuple[int, float] | None = None  # (count, timestamp)

    def record(self, category: str = "state_transition") -> bool:
        """Registra evento e verifica taxa. Retorna False se excedeu."""
        self._limiter.check(category)
        # if not allowed: alerta de taxa anormal já foi gerado pelo limiter
        return True

    def check_anomaly(self, window_seconds: int = 3600) -> dict[str, Any] | None:
        """Verifica se a taxa de transições está anormal vs baseline."""
        now = time.monotonic()
        row = self._db.fetchone(
            "SELECT COUNT(*) AS n, MAX(timestamp) AS last FROM state_transitions_audit"
        )
        count = row["n"] if row else 0

        if self._baseline is None:
            self._baseline = (count, now)
            return None

        base_count, base_time = self._baseline
        elapsed = now - base_time
        if elapsed <= 0:
            return None

        rate = (count - base_count) / (elapsed / window_seconds)
        if rate > 10:  # >10x o baseline por janela
            return {
                "anomaly": "high_transition_rate",
                "rate_per_window": round(rate, 2),
                "count": count,
                "baseline_count": base_count,
                "suggested": "read_only_mode",
                "at": datetime.now(timezone.utc).isoformat(),
            }
        return None