"""Testes de configuração — .env independente de cwd (H7),
provider failure explícito (H11), imutabilidade (H12)."""
import os
from pathlib import Path

import pytest

from mia_pkg.config import (
    Config, load_config, resolve_env_paths, _load_dotenv, _deep_freeze,
)


@pytest.fixture
def env_backup():
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


class TestDotenvResolution:
    def test_loads_from_config_dir(self, tmp_path, env_backup, monkeypatch):
        """~/.config/mia/.env (via config_dir) é carregado."""
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
        (tmp_path / "vazio").mkdir(exist_ok=True)
        monkeypatch.chdir(tmp_path / "vazio")  # cwd sem .env
        (tmp_path / "home" / ".config" / "mia").mkdir(parents=True)
        _write(tmp_path / "home" / ".config" / "mia", ".env", "OMNIROUTE_API_KEY=segredo-do-usuario\n")
        os.environ.pop("OMNIROUTE_API_KEY", None)
        cfg_dir = tmp_path / "home" / ".config" / "mia"
        load_config(cfg_dir)
        assert os.environ.get("OMNIROUTE_API_KEY") == "segredo-do-usuario"

    def test_mia_env_file_override(self, tmp_path, env_backup):
        """MIA_ENV_FILE aponta para caminho explícito."""
        explicit = _write(tmp_path, "custom.env", "MINHA_CHAVE=xpto\n")
        os.environ["MIA_ENV_FILE"] = str(explicit)
        load_config(tmp_path)
        assert os.environ.get("MINHA_CHAVE") == "xpto"

    def test_real_env_never_overwritten(self, tmp_path, env_backup, monkeypatch):
        """Variável de ambiente REAL tem precedência sobre .env."""
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
        os.environ["CHAVE_REAL"] = "real"
        cfg_dir = tmp_path / "home" / ".config" / "mia"
        cfg_dir.mkdir(parents=True)
        _write(cfg_dir, ".env", "CHAVE_REAL=arquivo\n")
        load_config(cfg_dir)
        assert os.environ["CHAVE_REAL"] == "real"  # não foi sobrescrita

    def test_resolve_env_paths_no_cwd_dependency(self, tmp_path, env_backup, monkeypatch):
        """resolve_env_paths não quebra sem .env no cwd."""
        monkeypatch.chdir(tmp_path)  # cwd sem .env
        paths = resolve_env_paths(tmp_path / "config")
        assert isinstance(paths, list)

    def test_load_dotenv_ignores_missing(self, tmp_path):
        """Arquivo .env inexistente → no-op (sem exceção)."""
        _load_dotenv(tmp_path / "nao-existe.env")  # não levanta


class TestProviderStatus:
    def _cfg(self, data):
        cfg = Config()
        object.__setattr__(cfg, "_data", _deep_freeze(data))
        return cfg

    def test_no_provider_configured(self, env_backup):
        cfg = self._cfg({"llm": {"providers": []}})
        status = cfg.provider_status()
        assert status["status"] == "NO_PROVIDER_CONFIGURED"

    def test_configured_provider_unavailable(self, env_backup):
        """Provider configurado mas chave ausente → CONFIGURED_PROVIDER_UNAVAILABLE."""
        os.environ.pop("CHAVE_X", None)
        cfg = self._cfg({
            "llm": {"providers": [{"name": "x", "api_key_env": "CHAVE_X"}]}
        })
        status = cfg.provider_status()
        assert status["providers"]["x"] == "CONFIGURED_PROVIDER_UNAVAILABLE"
        assert status["status"] == "NO_KEY"

    def test_ready_when_key_present(self, env_backup):
        os.environ["CHAVE_OK"] = "abc"
        cfg = self._cfg({
            "llm": {"providers": [{"name": "ok", "api_key_env": "CHAVE_OK"}]}
        })
        status = cfg.provider_status()
        assert status["providers"]["ok"] == "READY"
        assert status["status"] == "READY"

    def test_secret_never_exposed(self, env_backup):
        """provider_status não vaza o valor da chave."""
        os.environ["CHAVE_SECRETA"] = "super-secret-value-123"
        cfg = self._cfg({
            "llm": {"providers": [{"name": "s", "api_key_env": "CHAVE_SECRETA"}]}
        })
        out = cfg.provider_status()
        dumped = str(out)
        assert "super-secret-value-123" not in dumped


class TestConfigImmutability:
    def test_data_is_readonly(self):
        """Config._data não pode ser alterado externamente."""
        cfg = Config()
        with pytest.raises(TypeError):
            cfg._data["llm"] = {"outro": True}  # MappingProxyType

    def test_nested_immutable(self):
        """Sub-dicts também são imutáveis (deep freeze)."""
        cfg = Config()
        with pytest.raises(TypeError):
            cfg._data["llm"]["temperature"] = 999.0

    def test_lists_are_tuples(self):
        """Listas viram tuples (não mutáveis)."""
        cfg = Config()
        providers = cfg.get("llm.providers")
        assert isinstance(providers, tuple)

    def test_defaults_not_shared_mutable(self):
        """Config sem dados usa _DEFAULTS (não uma cópia mutável compartilhada)."""
        c1 = Config()
        c2 = Config()
        assert c1.get("llm.temperature") == c2.get("llm.temperature")
        # ambos leem o mesmo default congelado — leitura ok
        assert c1.get("system.name") == "Mia"