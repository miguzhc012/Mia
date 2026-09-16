"""BudgetAuthority — autoridade global de recursos e orçamento.

Conceito (H5 do hardening):

    Budget Authority (autoridade global)
        ↓ subordina
    local governors (OrchestrationGovernor, ResourceGovernor, RateLimiter,
    VisionRateLimiter, EmotionGovernor)

Cada governor local pode manter seus limites específicos (concorrência,
depth, tempo, janela). A BudgetAuthority impõe as REGRAS GLOBAIS que
nenhum governor local pode burlar:

- custo financeiro total (soma de custos de todos os governors)
- chamadas externas por dia (LLM/API/visão)
- tarefas autônomas por dia
- orçamento de runtime total

Escopo dos limites (H6):

- PROCESS-LOCAL: {concorrência, depth, janela de rate limit} — zerados
  no restart por natureza (são sobre execução em curso).
- SYSTEM/GLOBAL: {custo acumulado, chamadas por dia} — PERSISTIDOS em
  SQLite quando um db é fornecido. Restart do processo NÃO zera um
  limite global: o orçamento diário sobrevive ao processo.

Sem db (string vazia): fallback process-local com aviso explícito —
nunca silencioso.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mia_pkg.db import SQLiteConnection


@dataclass
class BudgetConfig:
    """Configuração global de orçamento."""
    max_daily_external_calls: int = 500    # LLM + visão + APIs externas
    max_daily_autonomous_actions: int = 50
    max_total_cost: float = 1000.0          # unidades abstratas de custo
    max_runtime_hours: float = 24.0         # runtime acumulado (soft)


@dataclass
class BudgetState:
    """Estado persistido/consultável do orçamento."""
    date: str = ""
    external_calls: int = 0
    autonomous_actions: int = 0
    total_cost: float = 0.0
    runtime_seconds: float = 0.0
    started_at: float = field(default_factory=time.monotonic)
    violations: list[dict[str, Any]] = field(default_factory=list)


class BudgetAuthority:
    """Autoridade global de orçamento — subordina governors locais."""

    def __init__(
        self,
        config: BudgetConfig | None = None,
        db: SQLiteConnection | None = None,
    ) -> None:
        self.config = config or BudgetConfig()
        self._db = db
        self._lock = threading.RLock()
        self._state = BudgetState()
        self._persistence_warning_logged = False
        if db is not None:
            self._ensure_table()
            self._load()

    # ------------------------------------------------------------------
    # Persistência (limites GLOBAIS sobrevivem ao processo)
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        try:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS budget_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    date TEXT NOT NULL,
                    external_calls INTEGER NOT NULL DEFAULT 0,
                    autonomous_actions INTEGER NOT NULL DEFAULT 0,
                    total_cost REAL NOT NULL DEFAULT 0.0,
                    runtime_seconds REAL NOT NULL DEFAULT 0.0
                )"""
            )
            self._db.commit()
        except Exception:
            # sem persistência disponível — continua em memória
            self._db = None

    def _load(self) -> None:
        if self._db is None:
            return
        try:
            row = self._db.fetchone(
                "SELECT * FROM budget_state WHERE id = 1"
            )
            today = self._today()
            if row:
                # custo acumulado e runtime são GLOBAIS — preserva sempre
                self._state.total_cost = row["total_cost"]
                self._state.runtime_seconds = row["runtime_seconds"]
            if row and row["date"] == today:
                self._state.date = row["date"]
                self._state.external_calls = row["external_calls"]
                self._state.autonomous_actions = row["autonomous_actions"]
            elif row and row["date"] != today:
                # dia novo: zera contadores diários, preserva custo global
                self._state.date = today
                self._state.external_calls = 0
                self._state.autonomous_actions = 0
                self._save()
        except Exception:
            self._db = None

    def _save(self) -> None:
        if self._db is None:
            if not self._persistence_warning_logged:
                print(
                    "[BudgetAuthority] aviso: sem persistência (db ausente) — "
                    "limites globais são process-local nesta instância"
                )
                self._persistence_warning_logged = True
            return
        try:
            self._db.execute(
                """INSERT INTO budget_state
                   (id, date, external_calls, autonomous_actions,
                    total_cost, runtime_seconds)
                   VALUES (1, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     date=excluded.date,
                     external_calls=excluded.external_calls,
                     autonomous_actions=excluded.autonomous_actions,
                     total_cost=excluded.total_cost,
                     runtime_seconds=excluded.runtime_seconds""",
                (
                    self._state.date,
                    self._state.external_calls,
                    self._state.autonomous_actions,
                    self._state.total_cost,
                    self._state.runtime_seconds,
                ),
            )
            self._db.commit()
        except Exception:
            pass  # persistência é best-effort

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def check_external_call(self) -> bool:
        """Registra uma chamada externa (LLM/API). False se estourou o dia."""
        with self._lock:
            if self._state.date != self._today():
                self._state.date = self._today()
                self._state.external_calls = 0
                self._state.autonomous_actions = 0
            if self._state.external_calls >= self.config.max_daily_external_calls:
                return False
            self._state.external_calls += 1
            self._save()
            return True

    def check_autonomous_action(self) -> bool:
        """Registra uma ação autônoma. False se estourou o dia."""
        with self._lock:
            if self._state.date != self._today():
                self._state.date = self._today()
                self._state.external_calls = 0
                self._state.autonomous_actions = 0
            if self._state.autonomous_actions >= self.config.max_daily_autonomous_actions:
                return False
            self._state.autonomous_actions += 1
            self._save()
            return True

    def spend(self, cost: float) -> bool:
        """Registra custo. False se o orçamento total foi excedido."""
        with self._lock:
            if self._state.total_cost + cost > self.config.max_total_cost:
                self._state.violations.append({
                    "type": "cost_exceeded",
                    "attempted": cost,
                    "total": self._state.total_cost,
                    "at": datetime.now(timezone.utc).isoformat(),
                })
                return False
            self._state.total_cost += cost
            self._save()
            return True

    def record_runtime(self, seconds: float) -> None:
        """Acumula runtime (soft limit — registra, não bloqueia)."""
        with self._lock:
            self._state.runtime_seconds += seconds
            self._save()

    def can_run(self) -> bool:
        """Autorização global: custo dentro + runtime soft ok."""
        with self._lock:
            if self._state.total_cost > self.config.max_total_cost:
                return False
            hours = self._state.runtime_seconds / 3600.0
            return hours <= self.config.max_runtime_hours

    # ------------------------------------------------------------------
    # Integração com governors locais (H5: subordinação)
    # ------------------------------------------------------------------

    def subordinated(self, governor: Any) -> "BudgetAuthority":
        """Declara um governor local como subordinado (verificação global).

        O governor local decide os limites LOCAIS; a BudgetAuthority
        verifica os limites GLOBAIS (custo/calls) na aquisição.
        """
        # Guarda referência para inspeção do orçamento
        self._subordinates: list[Any] = getattr(self, "_subordinates", [])
        if governor not in self._subordinates:
            self._subordinates.append(governor)
        return self

    @property
    def state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "date": self._state.date or self._today(),
                "external_calls": self._state.external_calls,
                "external_calls_max": self.config.max_daily_external_calls,
                "autonomous_actions": self._state.autonomous_actions,
                "autonomous_actions_max": self.config.max_daily_autonomous_actions,
                "total_cost": round(self._state.total_cost, 4),
                "total_cost_max": self.config.max_total_cost,
                "runtime_hours": round(self._state.runtime_seconds / 3600.0, 3),
                "runtime_hours_max": self.config.max_runtime_hours,
                "persisted": self._db is not None,
                "violations": list(self._state.violations),
            }

    def reset_daily(self) -> None:
        """Zera contadores diários (manutenção/teste)."""
        with self._lock:
            self._state.date = self._today()
            self._state.external_calls = 0
            self._state.autonomous_actions = 0
            self._save()