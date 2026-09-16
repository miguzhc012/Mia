"""Testes do Trust Boundary (H18/H19/H22) — identidade, kill switch, read-only."""
import pytest

from mia_pkg.trust import (
    ComponentKind, ComponentRegistry, IntegrityChecker,
    KillSwitch, ReadOnlyError, ReadOnlyMode,
)


class TestComponentRegistry:
    def test_register_and_authenticate(self):
        reg = ComponentRegistry()
        cmp = reg.register("perception", ComponentKind.ADAPTIVE)
        assert reg.authenticate("perception", cmp.token) is cmp
        assert reg.authenticate("perception", "token-errado") is None

    def test_declared_source_not_enough(self):
        """Afirmar source='state_authority' SEM token válido → não autentica."""
        reg = ComponentRegistry()
        reg.register("state_authority", ComponentKind.CORE, can_mutate_state=True)
        # impostor afirma ser a autoridade, mas não tem o token
        assert reg.authenticate("state_authority", "token-falso") is None
        assert reg.source_is_trusted("state_authority", "token-falso") is False

    def test_core_can_mutate_adaptive_cannot(self):
        reg = ComponentRegistry()
        reg.register("authority", ComponentKind.CORE, can_mutate_state=True)
        reg.register("mia", ComponentKind.ADAPTIVE)
        core = reg.authenticate("authority", reg._components["authority"].token)
        mia = reg.authenticate("mia", reg._components["mia"].token)
        assert reg.can_mutate_state("authority", core.token)
        assert not reg.can_mutate_state("mia", mia.token)

    def test_no_duplicate_registration(self):
        reg = ComponentRegistry()
        reg.register("x")
        with pytest.raises(ValueError):
            reg.register("x")

    def test_adaptive_cannot_mutate_trust(self):
        reg = ComponentRegistry()
        mia = reg.register("mia", ComponentKind.ADAPTIVE)
        assert mia.can_mutate_trust is False
        assert mia.can_mutate_state is False


class TestKillSwitch:
    def test_block_and_unblock(self):
        ks = KillSwitch()
        assert not ks.is_blocked()
        ks.block("perigo detectado")
        assert ks.is_blocked()
        ks.unblock()
        assert not ks.is_blocked()

    def test_history_recorded(self):
        ks = KillSwitch()
        ks.block("razão-a")
        ks.unblock()
        hist = ks.history()
        assert len(hist) == 2
        assert hist[0]["action"] == "block"
        assert hist[0]["reason"] == "razão-a"
        assert hist[1]["action"] == "unblock"


class TestReadOnlyMode:
    def test_enter_blocks_mutation(self):
        ro = ReadOnlyMode()
        ro.assert_mutable()  # ok
        ro.enter("anomalia")
        with pytest.raises(ReadOnlyError):
            ro.assert_mutable()
        ro.exit()
        ro.assert_mutable()  # ok de novo

    def test_info(self):
        ro = ReadOnlyMode()
        ro.enter("teste")
        info = ro.info()
        assert info["active"] is True
        assert info["reason"] == "teste"


class TestIntegrityChecker:
    def test_snapshot_verify(self):
        ic = IntegrityChecker()
        ic.snapshot("estado-a")
        assert ic.verify("estado-a")
        assert not ic.verify("estado-b")

    def test_verify_before_snapshot(self):
        ic = IntegrityChecker()
        assert not ic.verify("qualquer")  # sem snapshot anterior

    def test_corrupt(self):
        ic = IntegrityChecker()
        ic.snapshot("x")
        ic.corrupt()
        assert not ic.verify("x")