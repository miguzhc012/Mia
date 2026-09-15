"""Testes da Fase 15: Autoevolução (Evolution, Canary, Rollback, Imunidade)."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.evolution import (
    ParameterRegistry, EvolutionEngine, EvolutionProposal, ParameterProposal,
    CanaryDeployer, RollbackManager, IMMUNE_COMPONENTS,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
def registry():
    r = ParameterRegistry()
    r.register("affective_engine", "decay_rate", 0.05, 0.0, 0.5, "decai emoções")
    r.register("affective_engine", "mood_inertia", 0.7, 0.0, 1.0, "inércia do humor")
    r.register("memory", "consolidation_interval", 8, 1, 100, "turns p/ consolidar")
    return r


# ======================================================================
# Parameter Registry
# ======================================================================

class TestRegistry:
    def test_register_and_get(self, registry):
        assert registry.value("affective_engine", "decay_rate") == 0.05

    def test_set_within_range(self, registry):
        assert registry.set("affective_engine", "decay_rate", 0.1)
        assert registry.value("affective_engine", "decay_rate") == 0.1

    def test_set_outside_range_fails(self, registry):
        assert not registry.set("affective_engine", "decay_rate", 0.9)
        assert registry.value("affective_engine", "decay_rate") == 0.05

    def test_immune_component_cannot_register(self, registry):
        with pytest.raises(ValueError):
            registry.register("state_authority", "max_chain", 10, 0, 100)

    def test_list_all(self, registry):
        assert len(registry.list_all()) == 3


# ======================================================================
# Evolution Engine
# ======================================================================

class TestEvolution:
    def test_propose_improvement(self, registry):
        engine = EvolutionEngine(registry)
        prop = engine.propose_improvement(
            "affective_engine", "decay_rate", direction=+1, step=0.05,
            rationale="emoções duram demais",
        )
        assert prop.proposed_value == pytest.approx(0.1)
        assert prop.status == "pending"

    def test_proposal_clamped_to_range(self, registry):
        engine = EvolutionEngine(registry)
        prop = engine.propose_improvement(
            "affective_engine", "decay_rate", direction=+1, step=1.0,
        )
        assert prop.proposed_value <= prop.max_value

    def test_unknown_parameter_raises(self, registry):
        engine = EvolutionEngine(registry)
        with pytest.raises(ValueError):
            engine.propose_improvement("x", "y", direction=+1)

    def test_proposal_validation(self, registry):
        engine = EvolutionEngine(registry)
        prop = engine.propose_improvement(
            "affective_engine", "decay_rate", direction=+1, step=0.05,
        )
        ok, msg = prop.validate()
        assert ok

    def test_immune_component_proposal_rejected(self, registry):
        prop = ParameterProposal(
            component="policy_engine", parameter="max_delta",
            current_value=0.1, proposed_value=0.2,
            min_value=0.0, max_value=1.0,
        )
        ok, msg = prop.validate()
        assert not ok
        assert "imune" in msg

    def test_code_change_rejected(self, registry):
        engine = EvolutionEngine(registry)
        proposal = engine.propose_code_change("mudar meu core")
        assert proposal.code_change
        assert proposal.status == "rejected"


# ======================================================================
# Canary Deployer
# ======================================================================

class TestCanary:
    def test_deploy_canary_applies_values(self, registry):
        deployer = CanaryDeployer(registry)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        assert deployer.deploy_canary(proposal)
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.1)

    def test_promote_marks_active(self, registry):
        deployer = CanaryDeployer(registry)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        deployer.deploy_canary(proposal)
        assert deployer.promote(proposal)
        assert prop.status == "active"

    def test_rollback_restores(self, registry):
        deployer = CanaryDeployer(registry)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        deployer.deploy_canary(proposal)
        deployer.rollback()
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.05)
        assert prop.status == "rolled_back"

    def test_health_check_failure_triggers_rollback(self, registry):
        deployer = CanaryDeployer(registry, health_check=lambda: False)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        deployer.deploy_canary(proposal)
        ok = deployer.health_check_ok()
        assert not ok
        # rollback automático aconteceu
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.05)

    def test_code_change_canary_rejected(self, registry):
        deployer = CanaryDeployer(registry)
        proposal = EvolutionProposal(description="code", code_change=True)
        assert not deployer.deploy_canary(proposal)


# ======================================================================
# Rollback Manager
# ======================================================================

class TestRollbackManager:
    def test_snapshot_and_apply(self, registry):
        rm = RollbackManager(registry)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        snaps = rm.snapshot(proposal)
        assert len(snaps) == 1
        assert rm.apply(proposal)
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.1)

    def test_rollback_restores_all(self, registry):
        rm = RollbackManager(registry)
        props = [
            ParameterProposal(
                component="affective_engine", parameter="decay_rate",
                current_value=0.05, proposed_value=0.2,
                min_value=0.0, max_value=0.5,
            ),
            ParameterProposal(
                component="affective_engine", parameter="mood_inertia",
                current_value=0.7, proposed_value=0.9,
                min_value=0.0, max_value=1.0,
            ),
        ]
        proposal = EvolutionProposal(description="teste", parameters=props)
        rm.snapshot(proposal)
        rm.apply(proposal)
        assert rm.rollback() == 2
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.05)
        assert registry.value("affective_engine", "mood_inertia") == pytest.approx(0.7)

    def test_rollback_last_only(self, registry):
        rm = RollbackManager(registry)
        p1 = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        p2 = ParameterProposal(
            component="affective_engine", parameter="mood_inertia",
            current_value=0.7, proposed_value=0.8,
            min_value=0.0, max_value=1.0,
        )
        proposal = EvolutionProposal(description="teste", parameters=[p1, p2])
        rm.snapshot(proposal)
        rm.apply(proposal)
        rm.rollback_last()
        # último (mood_inertia) revertido, primeiro mantido
        assert registry.value("affective_engine", "mood_inertia") == pytest.approx(0.7)
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.1)

    def test_health_failure_rolls_back(self, registry):
        rm = RollbackManager(registry, health_check=lambda: False)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        rm.snapshot(proposal)
        rm.apply(proposal)
        ok = rm.health_check_ok()
        assert not ok
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.05)

    def test_apply_with_canary_success(self, registry):
        rm = RollbackManager(registry, health_check=lambda: True)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        assert rm.apply_with_canary(proposal, canary_seconds=0.01)
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.1)

    def test_apply_with_canary_failure_rolls_back(self, registry):
        rm = RollbackManager(registry, health_check=lambda: False)
        prop = ParameterProposal(
            component="affective_engine", parameter="decay_rate",
            current_value=0.05, proposed_value=0.1,
            min_value=0.0, max_value=0.5,
        )
        proposal = EvolutionProposal(description="teste", parameters=[prop])
        assert not rm.apply_with_canary(proposal, canary_seconds=0.01)
        assert registry.value("affective_engine", "decay_rate") == pytest.approx(0.05)


# ======================================================================
# Imunidade
# ======================================================================

class TestImmunity:
    def test_core_components_immune(self):
        assert "state_authority" in IMMUNE_COMPONENTS
        assert "policy_engine" in IMMUNE_COMPONENTS
        assert "cognitive_core" in IMMUNE_COMPONENTS
        assert "db" in IMMUNE_COMPONENTS