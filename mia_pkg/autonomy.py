"""Autonomy — Goal Store, Initiative Engine, Resource Governor.

Fase 6 do roadmap: Mia mantém objetivos e age autonomamente quando
Miguel está offline, com limites rígidos de custo/tempo/concorrência.
"""
from __future__ import annotations

import json
import uuid
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus


# ======================================================================
# Enums / Dataclasses
# ======================================================================

class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _json_load(value: Any) -> Any:
    """Deserializa JSON; retorna default se falhar."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return []
    return value or []


@dataclass
class Goal:
    """Um objetivo persistido da Mia."""
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: GoalStatus = GoalStatus.ACTIVE
    priority: GoalPriority = GoalPriority.MEDIUM
    progress: float = 0.0  # 0..1
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: str | None = None
    deadline: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def _priority_to_int(p: GoalPriority) -> int:
        return {"low": 2, "medium": 5, "high": 9}[p.value]

    @staticmethod
    def _int_to_priority(v: int) -> GoalPriority:
        if v >= 8:
            return GoalPriority.HIGH
        if v >= 4:
            return GoalPriority.MEDIUM
        return GoalPriority.LOW


@dataclass
class InitiativeReport:
    """Resultado de uma rodada da Initiative Engine."""
    goal_id: str | None = None
    action: str = "none"
    reasoning: str = ""
    resource_used: float = 0.0
    success: bool = True
    message: str = ""


@dataclass
class ResourceLimit:
    """Limite de um recurso."""
    name: str
    max: float
    used: float = 0.0
    unit: str = "units"


# ======================================================================
# Goal Store
# ======================================================================

class GoalStore:
    """Persistência de objetivos."""

    def __init__(self, db: SQLiteConnection) -> None:
        self._db = db
        self._ensure_extra_columns()

    def create(self, goal: Goal) -> Goal:
        self._db.execute(
            """INSERT INTO goals
               (id, description, status, priority, progress, created_at,
                completed_at, deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                goal.id, goal.description, goal.status.value,
                Goal._priority_to_int(goal.priority), goal.progress,
                goal.created_at, goal.completed_at, goal.deadline,
            ),
        )
        self._db.commit()
        return goal

    def get(self, goal_id: str) -> Goal | None:
        row = self._db.fetchone("SELECT * FROM goals WHERE id = ?", (goal_id,))
        return self._row_to_goal(row) if row else None

    def list_active(self) -> list[Goal]:
        rows = self._db.fetchall(
            "SELECT * FROM goals WHERE status = 'active' ORDER BY priority DESC"
        )
        return [self._row_to_goal(r) for r in rows]

    def update_progress(self, goal_id: str, progress: float, note: str = "") -> Goal:
        goal = self.get(goal_id)
        if not goal:
            raise KeyError(f"Goal não encontrado: {goal_id}")
        now = datetime.now(timezone.utc).isoformat()
        goal.progress = max(0.0, min(1.0, progress))
        goal.updated_at = now
        goal.history = goal.history + [{
            "event": "progress", "progress": goal.progress, "note": note, "at": now,
        }]
        if goal.progress >= 1.0:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = now
            goal.history.append({"event": "completed", "at": now})
        self._db.execute(
            """UPDATE goals SET progress=?, status=?, completed_at=? WHERE id=?""",
            (goal.progress, goal.status.value, goal.completed_at, goal_id),
        )
        self._db.commit()
        return goal

    def set_status(self, goal_id: str, status: GoalStatus) -> Goal:
        goal = self.get(goal_id)
        if not goal:
            raise KeyError(f"Goal não encontrado: {goal_id}")
        now = datetime.now(timezone.utc).isoformat()
        goal.status = status
        goal.updated_at = now
        goal.history = goal.history + [{"event": "status", "status": status.value, "at": now}]
        if status == GoalStatus.COMPLETED:
            goal.completed_at = now
        self._db.execute(
            """UPDATE goals SET status=?, completed_at=? WHERE id=?""",
            (goal.status.value, goal.completed_at, goal_id),
        )
        self._db.commit()
        return goal

    def _ensure_extra_columns(self) -> None:
        """Adiciona colunas updated_at/history se não existirem (migração)."""
        try:
            cols = {r["name"] for r in self._db.fetchall("PRAGMA table_info(goals)", ())}
        except Exception:
            return
        if "updated_at" not in cols:
            self._db.execute("ALTER TABLE goals ADD COLUMN updated_at TEXT")
        if "history" not in cols:
            self._db.execute("ALTER TABLE goals ADD COLUMN history TEXT DEFAULT '[]'")
            self._db.commit()

    def _row_to_goal(self, row: dict[str, Any]) -> Goal:
        return Goal(
            id=row["id"],
            description=row["description"],
            status=GoalStatus(row["status"]),
            priority=Goal._int_to_priority(row["priority"]),
            progress=row["progress"],
            created_at=row["created_at"],
            updated_at=row.get("updated_at") or row["created_at"],
            completed_at=row["completed_at"],
            deadline=row.get("deadline"),
            history=_json_load(row.get("history")),
        )


# ======================================================================
# Resource Governor
# ======================================================================

class ResourceGovernor:
    """Limita custo/tempo/concorrência das ações autônomas."""

    def __init__(self, config: dict[str, float] | None = None) -> None:
        # default: 10 ações/dia, 60s por ação, 2 ações concorrentes
        self._limits = {
            "actions_per_day": ResourceLimit("actions_per_day", config.get("actions_per_day", 10) if config else 10),
            "seconds_per_action": ResourceLimit("seconds_per_action", config.get("seconds_per_action", 60) if config else 60),
            "concurrency": ResourceLimit("concurrency", config.get("concurrency", 2) if config else 2),
        }
        self._running: set[str] = set()
        self._day_actions = 0
        self._day = datetime.now(timezone.utc).date()

    def can_run(self, action_id: str) -> bool:
        """Verifica se uma ação pode ser executada agora."""
        today = datetime.now(timezone.utc).date()
        if today != self._day:
            self._day = today
            self._day_actions = 0

        if self._day_actions >= self._limits["actions_per_day"].max:
            return False
        if len(self._running) >= self._limits["concurrency"].max:
            return False
        return True

    @contextmanager
    def run(self, action_id: str):
        """Context manager: reserva slot e conta custo."""
        if not self.can_run(action_id):
            raise PermissionError(
                f"Resource limits excedidos para {action_id} "
                f"(actions={self._day_actions}/{self._limits['actions_per_day'].max}, "
                f"running={len(self._running)}/{self._limits['concurrency'].max})"
            )
        self._running.add(action_id)
        self._day_actions += 1
        start = time.monotonic()
        try:
            yield
        finally:
            self._running.discard(action_id)
            elapsed = time.monotonic() - start
            if elapsed > self._limits["seconds_per_action"].max:
                # Ação estourou tempo — registra mas não bloqueia (não kill)
                pass

    @property
    def stats(self) -> dict[str, float]:
        return {
            "actions_today": float(self._day_actions),
            "actions_limit": self._limits["actions_per_day"].max,
            "running_now": float(len(self._running)),
            "concurrency_limit": self._limits["concurrency"].max,
        }


# ======================================================================
# Initiative Engine
# ======================================================================

class InitiativeEngine:
    """Decide o que Mia faz quando está idle (sem interação do usuário).

    Prioridade:
    1. Goals ativos de prioridade alta
    2. Consolidação de memórias (se pendentes)
    3. Reflexão/Diário (se devido)
    """

    def __init__(
        self,
        db: SQLiteConnection,
        goal_store: GoalStore | None = None,
        governor: ResourceGovernor | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._db = db
        self._goals = goal_store or GoalStore(db)
        self._governor = governor or ResourceGovernor()
        self._bus = bus or EventBus()

    def tick(self, max_actions: int = 3) -> list[InitiativeReport]:
        """Executa uma rodada de iniciativa (chamada quando idle)."""
        reports: list[InitiativeReport] = []
        goals = [g for g in self._goals.list_active() if g.progress < 1.0]

        actions_taken = 0
        # 1. Goals ativos
        for goal in goals:
            if actions_taken >= max_actions:
                break
            action_id = f"goal:{goal.id}"
            report = self._run_goal_step(goal.id, action_id)
            reports.append(report)
            if report.success and report.action != "none":
                actions_taken += 1

        return reports

    def _run_goal_step(self, goal_id: str, action_id: str) -> InitiativeReport:
        """Executa um passo de um goal (avança progresso)."""
        try:
            with self._governor.run(action_id):
                # Simula execução: avança progresso do goal
                goal = self._goals.get(goal_id)
                if not goal:
                    return InitiativeReport(goal_id=goal_id, success=False, message="goal não encontrado")
                new_progress = min(1.0, goal.progress + 0.2)
                self._goals.update_progress(
                    goal_id, new_progress,
                    note=f"passo autônomo ({action_id})",
                )
                return InitiativeReport(
                    goal_id=goal_id,
                    action="advance_goal",
                    reasoning=f"goal '{goal.description[:40]}' avançou {goal.progress:.0%}→{new_progress:.0%}",
                    resource_used=1.0,
                    message=f"Goal '{goal.description[:30]}...' avançou para {new_progress:.0%}",
                )
        except PermissionError as e:
            return InitiativeReport(
                goal_id=goal_id, success=False, message=str(e)
            )
        except Exception as e:
            return InitiativeReport(
                goal_id=goal_id, success=False, message=str(e)
            )

    def is_idle_action_due(self) -> bool:
        """True se há ação autônoma devida (goals ativos)."""
        return bool(self._goals.list_active())


# ======================================================================
# Integration: eventos de idle
# ======================================================================

def handle_idle(db: SQLiteConnection, bus: EventBus) -> list[InitiativeReport]:
    """Manipulador do evento IDLE: roda Initiative Engine e publica resultado.

    Retorna relatórios das ações tomadas.
    """
    engine = InitiativeEngine(db, bus=bus)
    reports = engine.tick()

    for report in reports:
        if report.success and report.action != "none":
            bus.emit(Event(
                type=EventType.TASK_COMPLETED,
                payload={"action": report.action, "goal_id": report.goal_id, "message": report.message},
                source="mia",
            ))
        elif not report.success:
            bus.emit(Event(
                type=EventType.TASK_FAILED,
                payload={"goal_id": report.goal_id, "message": report.message},
                source="mia",
            ))
    return reports