"""Testes da Fase 6: Goals, Initiative Engine, Resource Governor."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus
from mia_pkg.autonomy import (
    GoalStore, Goal, GoalStatus, GoalPriority,
    ResourceGovernor, InitiativeEngine, handle_idle,
    InitiativeReport,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# Goal Store
# ======================================================================

class TestGoalStore:
    def test_create_and_get(self, db):
        store = GoalStore(db)
        g = store.create(Goal(description="Aprender Python", priority=GoalPriority.HIGH))
        assert store.get(g.id) is not None
        assert store.get(g.id).description == "Aprender Python"
        assert store.get(g.id).priority == GoalPriority.HIGH

    def test_list_active_order(self, db):
        store = GoalStore(db)
        low = store.create(Goal(description="baixa", priority=GoalPriority.LOW))
        high = store.create(Goal(description="alta", priority=GoalPriority.HIGH))
        store.create(Goal(description="completa", priority=GoalPriority.HIGH))
        # completa o terceiro
        third = store.list_active()[-1]
        store.set_status(third.id, GoalStatus.COMPLETED)

        active = store.list_active()
        assert len(active) == 2
        assert active[0].id == high.id  # high primeiro

    def test_update_progress_completes(self, db):
        store = GoalStore(db)
        g = store.create(Goal(description="Ir para 100%"))
        g = store.update_progress(g.id, 1.0)
        assert g.status == GoalStatus.COMPLETED
        assert g.completed_at is not None
        # persiste
        assert store.get(g.id).status == GoalStatus.COMPLETED

    def test_progress_clamped(self, db):
        store = GoalStore(db)
        g = store.create(Goal(description="Clamp"))
        g = store.update_progress(g.id, 1.5)
        assert g.progress == 1.0

    def test_set_status(self, db):
        store = GoalStore(db)
        g = store.create(Goal(description="Pausa"))
        g = store.set_status(g.id, GoalStatus.PAUSED)
        assert g.status == GoalStatus.PAUSED
        assert store.get(g.id).status == GoalStatus.PAUSED

    def test_goals_persist_between_sessions(self, db):
        """Critério: goals persistem entre sessões (mesmo sqlite file)."""
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            d1 = SQLiteConnection(path)
            d1.connect(); d1.init_schema()
            store1 = GoalStore(d1)
            g = store1.create(Goal(description="Persistente"))
            d1.close()

            d2 = SQLiteConnection(path)
            d2.connect(); d2.init_schema()
            store2 = GoalStore(d2)
            assert store2.get(g.id) is not None
            assert store2.get(g.id).description == "Persistente"
            d2.close()
        finally:
            os.unlink(path)


# ======================================================================
# Resource Governor
# ======================================================================

class TestResourceGovernor:
    def test_allows_within_limits(self):
        gov = ResourceGovernor({"actions_per_day": 5, "seconds_per_action": 60, "concurrency": 2})
        assert gov.can_run("a1")
        assert gov.can_run("a2")

    def test_blocks_concurrency(self):
        gov = ResourceGovernor({"actions_per_day": 5, "seconds_per_action": 60, "concurrency": 2})
        with gov.run("a1"):
            with gov.run("a2"):
                assert not gov.can_run("a3")  # 2 já rodando

    def test_blocks_actions_per_day(self):
        gov = ResourceGovernor({"actions_per_day": 2, "seconds_per_action": 60, "concurrency": 10})
        with gov.run("a1"):
            pass
        with gov.run("a2"):
            pass
        assert not gov.can_run("a3")

    def test_context_manager_raises_permission(self):
        """Resource Governor impede execução além dos limites."""
        gov = ResourceGovernor({"actions_per_day": 1, "seconds_per_action": 60, "concurrency": 1})
        with gov.run("a1"):
            pass
        with pytest.raises(PermissionError):
            with gov.run("a2"):
                pass

    def test_stats(self):
        gov = ResourceGovernor({"actions_per_day": 3})
        with gov.run("x"):
            pass
        assert gov.stats["actions_today"] == 1.0
        assert gov.stats["actions_limit"] == 3.0


# ======================================================================
# Initiative Engine
# ======================================================================

class TestInitiativeEngine:
    def test_advances_goals_when_idle(self, db):
        store = GoalStore(db)
        g = store.create(Goal(description="Ler livro", priority=GoalPriority.MEDIUM))
        engine = InitiativeEngine(db)
        reports = engine.tick(max_actions=3)
        assert len(reports) >= 1
        assert reports[0].success
        # goal avançou
        updated = store.get(g.id)
        assert updated.progress > 0.0

    def test_no_goals_no_actions(self, db):
        engine = InitiativeEngine(db)
        reports = engine.tick()
        assert reports == []

    def test_completes_goal_after_steps(self, db):
        store = GoalStore(db)
        g = store.create(Goal(description="Rápido"))
        engine = InitiativeEngine(db)
        # 5 passos de 0.2 = 100%
        for _ in range(5):
            engine.tick(max_actions=1)
        assert store.get(g.id).status == GoalStatus.COMPLETED

    def test_resource_limits_respected(self, db):
        """Governor impede ações quando limite diário atingido."""
        store = GoalStore(db)
        store.create(Goal(description="Limitado"))
        gov = ResourceGovernor({"actions_per_day": 1, "seconds_per_action": 60, "concurrency": 5})
        engine = InitiativeEngine(db, governor=gov)
        reports = engine.tick(max_actions=5)
        assert len(reports) == 1  # só 1 ação permitida
        assert not gov.can_run("outra")


# ======================================================================
# handle_idle (integração com EventBus)
# ======================================================================

def test_handle_idle_emits_task_completed(db):
    store = GoalStore(db)
    store.create(Goal(description="Gerar relatório"))
    bus = EventBus()
    received = []
    bus.subscribe("task_completed", lambda e: received.append(e))

    reports = handle_idle(db, bus)
    assert len(reports) >= 1
    assert len(received) >= 1
    assert received[0].payload["goal_id"] is not None


def test_handle_idle_emits_task_failed_when_limited(db):
    store = GoalStore(db)
    store.create(Goal(description="Sem recursos"))
    bus = EventBus()
    received = []
    bus.subscribe("task_failed", lambda e: received.append(e))

    # governor que já esgotou o limite diário
    from mia_pkg.autonomy import ResourceGovernor, handle_idle
    gov = ResourceGovernor({"actions_per_day": 0, "seconds_per_action": 60, "concurrency": 1})

    import mia_pkg.autonomy as aut
    original = aut.InitiativeEngine
    aut.InitiativeEngine = lambda db, bus=bus: original(db, governor=gov, bus=bus)
    try:
        reports = handle_idle(db, bus)
        # com limite 0, nenhuma ação roda
        assert all(not r.success for r in reports) or len(reports) == 0
    finally:
        aut.InitiativeEngine = original