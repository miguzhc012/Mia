"""Config Manager — carrega config YAML/JSON de ~/.config/mia/ com defaults.

Secrets NUNCA são expostos ao LLM. Acessíveis apenas via Tool Gateway.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any


def _deep_freeze(value: Any) -> Any:
    """Torna uma estrutura de dicionários imutável recursivamente.

    dict → MappingProxyType (read-only, lança TypeError em escrita)
    list → tuple
    demais → inalterado (primitivos/None)
    """
    if isinstance(value, dict):
        return MappingProxyType({k: _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(v) for v in value)
    return value


# ======================================================================
# Defaults
# ======================================================================

_DEFAULTS: dict[str, Any] = {
    "system": {
        "name": "Mia",
        "version": "0.1.0",
        "debug": False,
    },
    "llm": {
        "providers": [
            {
                "name": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "api_key_env": "OPENAI_API_KEY",
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "memory": {
        "max_objects": 10000,
        "importance_threshold": 0.1,
        "consolidation_interval_hours": 24,
    },
    "security": {
        "kill_switch_path": "/var/mia/STOP",
        "max_emotion_transitions_per_hour": 10,
    },
    "event_bus": {
        "max_events_per_type_per_minute": 10,
        "circuit_breaker_threshold": 5,
    },
}


# ======================================================================
# Config class
# ======================================================================

@dataclass(frozen=True)
class Config:
    """Configuração imutável do sistema MIA.

    Segredos nunca são expostos — apenas referenciados via env var.
    `_data` é deep-frozen (MappingProxyType + tuples): qualquer tentativa
    de mutação externa lança TypeError em runtime.
    """

    _data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # sempre congela (inclusive _DEFAULTS) — MappingProxyType + tuples
        object.__setattr__(
            self, "_data", _deep_freeze(self._data if self._data else _DEFAULTS)
        )

    # ------------------------------------------------------------------
    # Acesso
    # ------------------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Acessa valor usando notação pontilhada: 'llm.temperature'."""
        keys = dotted_key.split(".")
        node: Any = self._data
        for k in keys:
            if isinstance(node, Mapping) and k in node:
                node = node[k]
            else:
                return default
        return node

    @property
    def data(self) -> dict[str, Any]:
        """Retorna cópia rasa dos dados (sem secrets)."""
        return {k: v for k, v in self._data.items()}

    def get_secret_ref(self, dotted_key: str) -> str | None:
        """Retorna o valor da env var referenciada, ou None.

        NUNCA armazena o secret em texto — apenas a referência.
        """
        env_var = self.get(dotted_key)
        if isinstance(env_var, str) and env_var:
            return os.environ.get(env_var)
        return None

    def provider_status(self) -> dict[str, Any]:
        """Diagnóstico dos providers (sem revelar secrets).

        Diferencia NO_PROVIDER_CONFIGURED de CONFIGURED_PROVIDER_UNAVAILABLE.
        """
        providers = self.get("llm.providers", [])
        if not providers:
            return {"status": "NO_PROVIDER_CONFIGURED"}
        resolved: dict[str, str] = {}
        for p in providers:
            env_name = p.get("api_key_env", "")
            key_present = bool(env_name and os.environ.get(env_name))
            resolved[p.get("name", "?")] = (
                "READY" if key_present else "CONFIGURED_PROVIDER_UNAVAILABLE"
            )
        overall = "READY" if all(v == "READY" for v in resolved.values()) else (
            "PARTIAL" if any(v == "READY" for v in resolved.values()) else "NO_KEY"
        )
        return {"status": overall, "providers": resolved}


# ======================================================================
# Loader
# ======================================================================

def _deep_merge(base: dict, override: dict) -> dict:
    """Mescla override sobre base recursivamente."""
    merged = base.copy()
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def _load_dotenv(path: Path) -> None:
    """Carrega variáveis de um arquivo .env para os.environ (sem sobrescrever).

    Formato: KEY=value (comentários # e linhas em branco ignorados).
    O arquivo é lido SOMENTE se o diretório existir (evita erros).
    """
    if not path.exists() or not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


# Precedência de resolução do .env (H7):
#   1. Variáveis de ambiente REAIS (maior) — nunca sobrescritas
#   2. MIA_ENV_FILE — caminho explícito/configurável
#   3. ~/.config/mia/.env  — secrets do usuário
#   4. .env da raiz do projeto — SOMENTE em desenvolvimento
# NUNCA depende de cwd.
def resolve_env_paths(config_dir: Path) -> list[Path]:
    """Retorna os caminhos de .env na ordem de precedência (menor→maior).

    Quanto mais tarde na lista, maior precedência (é lido por último,
    mas como _load_dotenv não sobrescreve env existente, o efeito é:
    primeiro lido = valor default; env real sempre vence).

    Ordem (do MENOR para o MAIOR):
      - .env da raiz do projeto (dev) — último
      - buscado de ~/.config/mia/.env
      - explicit MIA_ENV_FILE — primeiro na prática
    """
    paths: list[Path] = []

    # config_dir/.env (secrets locais da instância) — menor precedência
    # entre os de arquivo? Não: queremos que o do config_dir VENÇA o do
    # projeto. Então o projeto vem PRIMEIRO (menor), config_dir depois.

    # 4 (menor): raiz do projeto (desenvolvimento apenas)
    for start in [Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (start / ".env").exists() and (start / ".env") not in paths:
            paths.append(start / ".env")

    # 3: config_dir/.env — a própria pasta de config da instância
    if (config_dir / ".env").exists() and (config_dir / ".env") not in paths:
        paths.append(config_dir / ".env")

    # 2: ~/.config/mia/.env (secrets do usuário)
    user_env = Path.home() / ".config" / "mia" / ".env"
    if user_env.exists() and user_env not in paths:
        paths.append(user_env)

    # 1 (maior entre arquivos): MIA_ENV_FILE explícito
    explicit = os.environ.get("MIA_ENV_FILE")
    if explicit:
        ep = Path(explicit).expanduser()
        if ep.exists() and ep not in paths:
            paths.append(ep)

    return paths


def _provider_status(data: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    """Diagnóstico: quais providers estão CONFIGURADOS e quais têm CHAVE.

    Sem revelar secrets. Diferencia:
      NO_PROVIDER_CONFIGURED        — nenhum provider no config
      CONFIGURED_PROVIDER_UNAVAILABLE — provider existe, chave ausente
      READY                         — provider + chave (via env real)
    """
    providers = data.get("llm", {}).get("providers", [])
    if not providers:
        return {"status": "NO_PROVIDER_CONFIGURED"}
    resolved: dict[str, str] = {}
    for p in providers:
        env_name = p.get("api_key_env", "")
        key_present = bool(env_name and os.environ.get(env_name))
        resolved[p.get("name", "?")] = (
            "READY" if key_present else "CONFIGURED_PROVIDER_UNAVAILABLE"
        )
    return {"status": "MIXED" if any(v == "READY" for v in resolved.values()) else "NO_KEY", "providers": resolved}


def load_config(config_dir: str | Path | None = None) -> Config:
    """Carrega configuração de ~/.config/mia/ (YAML ou JSON).

    1. Carrega .env do diretório do projeto (se existir).
    2. Começa com defaults.
    3. Aplica overrides do arquivo de config.
    4. Aplica overrides de variáveis de ambiente (MIA_*).

    Returns:
        Config com dados mesclados.
    """
    if config_dir is None:
        config_dir = Path.home() / ".config" / "mia"
    else:
        config_dir = Path(config_dir)

    # Carrega .env na ordem de precedência (H7): env real > MIA_ENV_FILE
    # > ~/.config/mia/.env > config_dir/.env > .env do projeto (dev).
    # _load_dotenv NÃO sobrescreve env existente → percorremos do MAIOR
    # para o MENOR: o mais específico carrega primeiro e vence.
    for env_path in reversed(resolve_env_paths(config_dir)):
        _load_dotenv(env_path)

    data = _DEFAULTS.copy()

    # Tenta YAML primeiro, depois JSON
    for filename in ["config.yaml", "config.yml", "config.json"]:
        config_file = config_dir / filename
        if config_file.exists():
            file_data = _load_file(config_file)
            data = _deep_merge(data, file_data)
            break

    # Overrides via env vars: MIA_<SECTION>_<KEY>=<value>
    for key, value in os.environ.items():
        if key.startswith("MIA_"):
            parts = key[4:].lower().split("_", 1)
            if len(parts) == 2:
                section, field_name = parts
                if section in data and isinstance(data[section], dict):
                    data[section][field_name] = value

    return Config(_data=data)


def _load_file(path: Path) -> dict[str, Any]:
    """Carrega arquivo YAML ou JSON."""
    content = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]
            return yaml.safe_load(content) or {}
        except ImportError:
            # Sem PyYAML — tenta interpretar como JSON
            return json.loads(content)
    else:
        return json.loads(content)
