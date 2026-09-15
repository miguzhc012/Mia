"""Runtime — lifecycle do sistema MIA.

Inicializa config, event bus, db, registra shutdown hooks.
"""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path
from typing import Any

from mia_pkg.config import Config, load_config
from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus
from mia_pkg.memory import MemoryStore
from mia_pkg.policy_engine import PolicyEngine
from mia_pkg.state_authority import StateAuthority

logger = logging.getLogger(__name__)


class Runtime:
    """Lifecycle do sistema MIA.

    Inicialização: config → db → event bus → state authority → memory store.
    Shutdown: graceful com hooks.
    """

    def __init__(self, config_dir: str | Path | None = None, db_path: str | Path | None = None) -> None:
        self._config = load_config(config_dir)
        self._db_path = db_path or Path.home() / ".local" / "share" / "mia" / "mia.db"
        self._db = SQLiteConnection(self._db_path)
        self._event_bus = EventBus(
            circuit_breaker_threshold=self._config.get(
                "event_bus.circuit_breaker_threshold", 5
            )
        )
        self._policy_engine = PolicyEngine(
            max_emotion_transitions_per_hour=self._config.get(
                "security.max_emotion_transitions_per_hour", 10
            )
        )
        self._state_authority = StateAuthority(
            db=self._db,
            policy_engine=self._policy_engine,
            event_bus=self._event_bus,
        )
        self._memory_store = MemoryStore(self._db)
        self._shutdown_hooks: list[Any] = []
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicializa todos os componentes."""
        logger.info("Iniciando MIA Runtime v%s", self._config.get("system.version"))

        # Cria diretório do banco se necessário
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Conecta ao banco
        self._db.connect()
        self._db.init_schema()
        logger.info(
            "Banco conectado: %s (schema v%d)",
            self._db_path,
            self._db.get_schema_version(),
        )

        # Registra signal handlers para shutdown graceful
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self._running = True
        logger.info("MIA Runtime iniciado com sucesso.")

    def stop(self) -> None:
        """Shutdown graceful — executa hooks e fecha conexões."""
        logger.info("Parando MIA Runtime...")
        self._running = False

        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception:
                logger.exception("Erro ao executar shutdown hook.")

        self._db.close()
        logger.info("MIA Runtime parado.")

    def register_shutdown_hook(self, hook: Any) -> None:
        """Registra função a ser chamada no shutdown."""
        self._shutdown_hooks.append(hook)

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handler para sinais de shutdown."""
        self.stop()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Acesso aos componentes
    # ------------------------------------------------------------------

    @property
    def config(self) -> Config:
        return self._config

    @property
    def db(self) -> SQLiteConnection:
        return self._db

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def state_authority(self) -> StateAuthority:
        return self._state_authority

    @property
    def memory_store(self) -> MemoryStore:
        return self._memory_store

    @property
    def policy_engine(self) -> PolicyEngine:
        return self._policy_engine

    @property
    def is_running(self) -> bool:
        return self._running
