"""Testes do Trust Boundary (H18/H19/H22) — identidade, kill switch, read-only."""
import secrets

import pytest

from mia_pkg.trust import (
    ComponentKind, ComponentRegistry, IntegrityChecker,
    KillSwitch, KillSwitchAuthError, ReadOnlyError, ReadOnlyMode,
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
        core = reg.register("authority", ComponentKind.CORE, can_mutate_state=True)
        mia = reg.register("mia", ComponentKind.ADAPTIVE)
        assert reg.can_mutate_state("authority", core.token)
        assert not reg.can_mutate_state("mia", mia.token)

    def test_token_not_exposed_in_repr(self):
        """Token NÃO aparece em repr/logs (vazamento de segredo)."""
        reg = ComponentRegistry()
        cmp = reg.register("autoridade", ComponentKind.CORE, can_mutate_state=True)
        assert cmp.token not in repr(cmp)

    def test_public_dict_never_includes_token(self):
        """public_dict() é a serialização segura — NUNCA expõe o token."""
        reg = ComponentRegistry()
        cmp = reg.register("autoridade", ComponentKind.CORE, can_mutate_state=True)
        d = cmp.public_dict()
        assert "_token" not in d
        assert cmp.token not in repr(d)
        assert d["name"] == "autoridade"
        assert d["kind"] == "core"

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

    def test_register_adaptive_with_trust_rejected(self):
        """ADAPTIVE com can_mutate_trust=True é REJEITADO (enforced)."""
        reg = ComponentRegistry()
        with pytest.raises(ValueError):
            reg.register("mia_bad", ComponentKind.ADAPTIVE, can_mutate_trust=True)

    def test_register_external_with_mutation_rejected(self):
        """EXTERNAL com can_mutate_state/trust=True é REJEITADO (enforced)."""
        reg = ComponentRegistry()
        with pytest.raises(ValueError):
            reg.register("ext_bad", ComponentKind.EXTERNAL, can_mutate_state=True)
        with pytest.raises(ValueError):
            reg.register("ext_bad2", ComponentKind.EXTERNAL, can_mutate_trust=True)

    def test_register_core_with_mutation_ok(self):
        """CORE autorizado pode mutar estado (authority legítima)."""
        reg = ComponentRegistry()
        core = reg.register("authority", ComponentKind.CORE, can_mutate_state=True)
        assert reg.can_mutate_state("authority", core.token) is True


class TestKillSwitch:
    def test_block_and_unblock_with_token(self):
        ks = KillSwitch(owner_token="segredo")
        assert not ks.is_blocked()
        ks.block("perigo detectado", token="segredo")
        assert ks.is_blocked()
        ks.unblock(token="segredo")
        assert not ks.is_blocked()

    def test_block_without_token_rejected(self):
        ks = KillSwitch(owner_token="segredo")
        with pytest.raises(KillSwitchAuthError):
            ks.block("perigo", token="")
        assert not ks.is_blocked()  # nada mudou

    def test_unblock_without_token_rejected(self):
        ks = KillSwitch(owner_token="segredo")
        ks.block("perigo", token="segredo")
        with pytest.raises(KillSwitchAuthError):
            ks.unblock(token="")
        assert ks.is_blocked()  # continua bloqueado

    def test_wrong_token_rejected(self):
        ks = KillSwitch(owner_token="segredo")
        with pytest.raises(KillSwitchAuthError):
            ks.block("perigo", token="outro-token")
        assert not ks.is_blocked()

    def test_fail_closed_without_owner_key(self):
        """Sem a chave do owner, o kill switch NÃO pode ser operado (fail-closed)."""
        ks = KillSwitch(owner_token=secrets.token_urlsafe(32))
        with pytest.raises(KillSwitchAuthError):
            ks.block("qualquer")
        assert not ks.is_blocked()

    def test_non_string_token_raises_killswitch_error(self):
        """token=None/int/bytes → KillSwitchAuthError, NUNCA TypeError cru."""
        ks = KillSwitch(owner_token="segredo")
        for bad in (None, 123, b"segredo"):
            with pytest.raises(KillSwitchAuthError):
                ks.block("perigo", token=bad)  # type: ignore[arg-type]
        # também no unblock
        for bad in (None, 123, b"segredo"):
            with pytest.raises(KillSwitchAuthError):
                ks.unblock(token=bad)  # type: ignore[arg-type]
        assert not ks.is_blocked()

    def test_non_string_owner_token_rejected(self):
        """owner_token não-str no init → TypeError claro."""
        with pytest.raises(TypeError):
            KillSwitch(owner_token=None)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            KillSwitch(owner_token=123)  # type: ignore[arg-type]

    def test_history_recorded(self):
        ks = KillSwitch(owner_token="segredo")
        ks.block("razão-a", token="segredo")
        ks.unblock(token="segredo")
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

    def test_no_corrupt_method_exposed(self):
        """NENHUM método público zera a integridade — nem _corrupt."""
        ic = IntegrityChecker()
        assert not hasattr(ic, "corrupt")
        assert not hasattr(ic, "_corrupt")
        ic.snapshot("x")
        assert ic.verify("x")