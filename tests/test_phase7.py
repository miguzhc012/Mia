"""Testes da Fase 8: Security Hardening (Redactor, Rate Limiter, Integrity, Sandbox)."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.security import (
    SecretsRedactor, RateLimiter, RateLimitConfig,
    IntegrityChecker, Sandbox, AuditMonitor,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


# ======================================================================
# Secrets Redactor
# ======================================================================

class TestSecretsRedactor:
    def test_redacts_openai_key(self):
        r = SecretsRedactor()
        text = "minha chave é sk-abc123xyz789opq456rstuvw and mais"
        out = r.redact(text)
        assert "sk-abc123xyz789opq456rstuvw" not in out
        assert "[openai_key:***]" in out

    def test_redacts_bearer(self):
        r = SecretsRedactor()
        out = r.redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.token.secret")
        assert "eyJhbGciOiJIUzI1NiJ9" not in out
        assert "[bearer_token:***]" in out

    def test_redacts_password(self):
        r = SecretsRedactor()
        out = r.redact("password=minhasenha123 and login=user")
        assert "minhasenha123" not in out
        assert "[password:***]" in out

    def test_redacts_private_key_header(self):
        r = SecretsRedactor()
        out = r.redact("chave: -----BEGIN RSA PRIVATE KEY----- abcdef")
        assert "BEGIN RSA" not in out

    def test_contains_secret(self):
        r = SecretsRedactor()
        assert r.contains_secret("chave api_key=1234567890abcdef")
        assert not r.contains_secret("olá mundo normal")


# ======================================================================
# Rate Limiter
# ======================================================================

class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = RateLimiter([RateLimitConfig("test_a", max_events=5, window_seconds=60)])
        for _ in range(5):
            assert limiter.check("test_a")

    def test_blocks_over_limit(self):
        limiter = RateLimiter([RateLimitConfig("test_b", max_events=2, window_seconds=60)])
        assert limiter.check("test_b")
        assert limiter.check("test_b")
        assert not limiter.check("test_b")  # bloqueado

    def test_read_only_after_exhaustion(self):
        limiter = RateLimiter([RateLimitConfig("test_c", max_events=1, window_seconds=60)])
        limiter.check("test_c")
        assert not limiter.check("test_c")
        # após exceder, read_only é ativado
        assert limiter.status()["read_only"] is True

    def test_unknown_category_unlimited(self):
        limiter = RateLimiter()
        assert limiter.check("categoria_nova")  # não limitada

    def test_status_reports_ratios(self):
        limiter = RateLimiter([RateLimitConfig("test_d", max_events=10, window_seconds=60)])
        limiter.check("test_d")
        limiter.check("test_d")
        status = limiter.status()
        assert status["limits"]["test_d"]["count"] == 2
        assert status["limits"]["test_d"]["ratio"] == pytest.approx(0.2)

    def test_alerts_after_threshold(self):
        limiter = RateLimiter([RateLimitConfig("test_e", max_events=10, window_seconds=60, alert_threshold=0.5)])
        for _ in range(5):
            limiter.check("test_e")
        assert len(limiter.status()["alerts"]) >= 1


# ======================================================================
# Integrity Checker
# ======================================================================

class TestIntegrityChecker:
    def test_verify_empty_db(self, db):
        checker = IntegrityChecker(db)
        ok, count, errors = checker.check_now()
        assert ok is True
        assert count == 0

    def test_verify_after_transitions(self, db):
        """Hash chain íntegra depois de transições via State Authority."""
        from mia_pkg.state_authority import StateAuthority
        from mia_pkg.policy_engine import PolicyEngine, StateTransitionProposal
        sa = StateAuthority(db, PolicyEngine(db))
        for i in range(5):
            sa.propose(StateTransitionProposal(
                target="emotion", action="update", key="happiness", delta=0.1, source="test"
            ))
        checker = IntegrityChecker(db)
        ok, count, errors = checker.check_now()
        assert ok is True
        assert count == 5
        assert errors == []

    def test_verify_detects_tampering(self, db):
        """Hash chain detecta adulteração do audit log."""
        from mia_pkg.state_authority import StateAuthority
        from mia_pkg.policy_engine import PolicyEngine, StateTransitionProposal
        sa = StateAuthority(db, PolicyEngine(db))
        sa.propose(StateTransitionProposal(
            target="emotion", action="update", key="happiness", delta=0.1, source="test"
        ))
        # Adultera o log diretamente
        db.execute("UPDATE state_transitions_audit SET after_snapshot = 'HACKED'")
        db.commit()
        checker = IntegrityChecker(db)
        ok, count, errors = checker.check_now()
        assert ok is False
        assert len(errors) >= 1


# ======================================================================
# Sandbox
# ======================================================================

class TestSandbox:
    def test_blocks_dangerous_code(self, db):
        s = Sandbox(db)
        ok, errors = s.validate_code("os.system('rm -rf /')")
        assert ok is False
        assert any("os.system" in e for e in errors)

    def test_allows_safe_code(self, db):
        s = Sandbox(db)
        ok, errors = s.validate_code("import math; result = math.sqrt(16)")
        assert ok is True
        assert errors == []

    def test_blocks_dangerous_imports(self, db):
        s = Sandbox(db)
        ok, errors = s.validate_imports("import subprocess")
        assert ok is False
        assert any("subprocess" in e for e in errors)

    def test_allows_safe_imports(self, db):
        s = Sandbox(db)
        ok, errors = s.validate_imports("import json\nimport math")
        assert ok is True

    def test_audit_action(self, db):
        s = Sandbox(db)
        s.audit_action("run_script", "print('hi')", True, "código seguro")
        row = db.fetchone("SELECT * FROM sandbox_actions")
        assert row is not None
        assert row["allowed"] == 1
        assert row["reason"] == "código seguro"

    def test_audit_rejected_action(self, db):
        s = Sandbox(db)
        s.audit_action("run_script", "os.system('x')", False, "código bloqueado")
        row = db.fetchone("SELECT * FROM sandbox_actions")
        assert row["allowed"] == 0


# ======================================================================
# Audit Monitor
# ======================================================================

class TestAuditMonitor:
    def test_record_and_anomaly(self, db):
        monitor = AuditMonitor(db)
        assert monitor.record()  # registra
        anomaly = monitor.check_anomaly()
        assert anomaly is None  # baseline ainda

        # muitas transições rápidas → anomalia
        for i in range(20):
            db.execute(
                "INSERT INTO state_transitions_audit "
                "(id, timestamp, component_origin, transition_type, target, key, "
                "before_snapshot, after_snapshot, evidence, confidence, applied_by, "
                "proposal_id, hash, hash_prev) "
                "VALUES (?, ?, 'test', 'update', 'emotion', 'happiness', '{}', '{}', '', 0.5, "
                "'test', 'test', 'hash', 'prev')",
                (f"id-{i}", "2026-01-01T00:00:00"),
            )
        db.commit()
        anomaly = monitor.check_anomaly(window_seconds=60)
        assert anomaly is not None
        assert anomaly["anomaly"] == "high_transition_rate"