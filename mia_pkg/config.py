"""Config Manager — carrega config YAML/JSON de ~/.config/mia/ com defaults.

Secrets NUNCA são expostos ao LLM. Acessíveis apenas via Tool Gateway.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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

@dataclass
class Config:
    """Configuração imutável do sistema MIA.

    Segredos nunca são expostos — apenas referenciados via env var.
    """

    _data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self._data:
            self._data = _DEFAULTS.copy()

    # ------------------------------------------------------------------
    # Acesso
    # ------------------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Acessa valor usando notação pontilhada: 'llm.temperature'."""
        keys = dotted_key.split(".")
        node: Any = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
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
    """
    if not path.exists():
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

    # Carrega .env do projeto (raiz do cwd) para chaves não ficarem
    # dependentes de export manual.
    _load_dotenv(Path.cwd() / ".env")

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
