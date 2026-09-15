"""Distributed Nodes — Node Manager, Sync Engine, Offline Mode, Conflict Resolver.

Fase 12 do roadmap:
- Node Manager: detecta e gerencia nós (id, papel, status)
- Sync Engine: snapshot SQLite + eventos entre nós (fila simples)
- Offline Mode: funciona com último snapshot
- Conflict Resolver: escritas roteadas ao VPS (master); master wins

Design:
- Master = VPS (escritas autorizadas); Clients = PC/mobile (leitura + fila)
- Snapshot = dump serializado do SQLite (JSON das tabelas principais)
- Sync bidirecional: client → master (eventos/fila), master → client (snapshot)
- Offline: client opera com snapshot local, enfileira eventos, sincroniza depois
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus

logger = logging.getLogger(__name__)


# ======================================================================
# Tipos
# ======================================================================

class NodeRole(str, Enum):
    MASTER = "master"      # VPS — autoridade de escrita
    CLIENT = "client"      # PC/mobile — leitura + fila de eventos


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    SYNCING = "syncing"


@dataclass
class Node:
    """Um nó no cluster."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "node"
    role: NodeRole = NodeRole.CLIENT
    status: NodeStatus = NodeStatus.OFFLINE
    last_seen_s: float = field(default_factory=time.time)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        d["status"] = self.status.value
        return d


@dataclass
class SyncEvent:
    """Evento enfileirado para sync entre nós."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "state_change"   # state_change | memory | event
    payload: dict[str, Any] = field(default_factory=dict)
    node_id: str = "local"
    created_s: float = field(default_factory=time.time)
    applied: bool = False


@dataclass
class SyncSnapshot:
    """Snapshot serializado do estado (tabelas principais)."""
    node_id: str
    created_s: float
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    checksum: str = ""

    def compute_checksum(self) -> str:
        """MD5 do conteúdo — detecta divergência."""
        canonical = json.dumps(self.tables, sort_keys=True, default=str)
        return hashlib.md5(canonical.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ======================================================================
# Node Manager
# ======================================================================

class NodeManager:
    """Registra, monitora e gerencia nós."""

    def __init__(self, db: SQLiteConnection, bus: EventBus | None = None,
                 role: NodeRole = NodeRole.CLIENT, name: str = "local") -> None:
        self._db = db
        self._bus = bus or EventBus()
        self._nodes: dict[str, Node] = {}
        self._local = Node(name=name, role=role, status=NodeStatus.ONLINE)
        self._register(self._local)

    def _register(self, node: Node) -> None:
        self._nodes[node.id] = node

    def local(self) -> Node:
        return self._local

    def register_peer(self, node_id: str, name: str, role: NodeRole) -> Node:
        """Registra um nó remoto."""
        node = Node(id=node_id, name=name, role=role, status=NodeStatus.ONLINE)
        self._nodes[node_id] = node
        self._bus.emit(Event(
            type=EventType.NODE_ONLINE,
            payload={"node_id": node_id, "name": name, "role": role.value},
            source="node_manager",
        ))
        return node

    def mark_offline(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node:
            node.status = NodeStatus.OFFLINE
        self._bus.emit(Event(
            type=EventType.NODE_OFFLINE,
            payload={"node_id": node_id},
            source="node_manager",
        ))

    def heartbeat(self, node_id: str) -> None:
        """Atualiza last_seen. Se desconhecido, registra."""
        node = self._nodes.get(node_id)
        if node:
            node.last_seen_s = time.time()
            node.status = NodeStatus.ONLINE
        else:
            self.register_peer(node_id, node_id, NodeRole.CLIENT)

    def list_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def get(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def is_master(self) -> bool:
        return self._local.role == NodeRole.MASTER


# ======================================================================
# Sync Engine
# ======================================================================

class SyncEngine:
    """Sincroniza snapshots + fila de eventos entre nós.

    Master route: client envia eventos → master aplica → master devolve
    snapshot → client atualiza. Master wins em conflito (R12.1: simples,
    sem CRDTs).
    """

    # tabelas sincronizadas (evita tabelas derivadas/logs)
    SYNC_TABLES = [
        "memory_objects", "beliefs", "people", "relationships",
        "identity_state", "personality_state", "emotion_state",
        "goals", "needs",
    ]

    def __init__(self, db: SQLiteConnection, node: NodeManager,
                 bus: EventBus | None = None) -> None:
        self._db = db
        self._node = node
        self._bus = bus or EventBus()
        self._queue: list[SyncEvent] = []

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def create_snapshot(self) -> SyncSnapshot:
        """Serializa tabelas principais."""
        tables: dict[str, list[dict[str, Any]]] = {}
        for table in self.SYNC_TABLES:
            try:
                rows = self._db.fetchall(f"SELECT * FROM {table}")
                tables[table] = [dict(r) for r in rows]
            except Exception:
                tables[table] = []  # tabela não existe ainda (schema diferido)
        snap = SyncSnapshot(
            node_id=self._node.local().id,
            created_s=time.time(),
            tables=tables,
        )
        snap.checksum = snap.compute_checksum()
        return snap

    def apply_snapshot(self, snap: SyncSnapshot) -> int:
        """Aplica snapshot remoto localmente. Retorna qtd de linhas substituídas.

        Substitui tabelas alvo inteiras (master wins: snapshot do master
        sobrepõe estado local do client).
        """
        if snap.checksum and snap.checksum != snap.compute_checksum():
            logger.warning("checksum mismatch no snapshot %s", snap.node_id)
            return 0

        applied = 0
        for table, rows in snap.tables.items():
            if table not in self.SYNC_TABLES:
                continue
            try:
                self._db.execute(f"DELETE FROM {table}")
                for row in rows:
                    cols = ", ".join(row.keys())
                    placeholders = ", ".join("?" for _ in row)
                    self._db.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                        tuple(row.values()),
                    )
                    applied += 1
                self._db.commit()
            except Exception as e:
                logger.error("falha ao aplicar %s: %s", table, e)
        self._bus.emit(Event(
            type=EventType.SYNC_COMPLETED,
            payload={"from": snap.node_id, "applied": applied},
            source="sync_engine",
        ))
        return applied

    # ------------------------------------------------------------------
    # Fila de eventos (offline → sync)
    # ------------------------------------------------------------------

    def enqueue(self, event_type: str, payload: dict[str, Any]) -> SyncEvent:
        """Enfileira evento para sync (quando online, enviado ao master)."""
        ev = SyncEvent(
            type=event_type,
            payload=payload,
            node_id=self._node.local().id,
        )
        self._queue.append(ev)
        return ev

    def pending_events(self) -> list[SyncEvent]:
        return [e for e in self._queue if not e.applied]

    def flush_queue(self, apply_fn: Callable[[SyncEvent], bool]) -> int:
        """Tenta aplicar eventos pendentes; marca applied se OK."""
        sent = 0
        for ev in self._queue:
            if ev.applied:
                continue
            try:
                if apply_fn(ev):
                    ev.applied = True
                    sent += 1
            except Exception:
                logger.warning("evento %s falhou no flush (fica na fila)", ev.id)
        return sent

    def serialize_queue(self) -> str:
        return json.dumps([asdict(e) for e in self._queue], default=str)

    def load_queue(self, raw: str) -> None:
        if not raw:
            return
        try:
            data = json.loads(raw)
            self._queue = [SyncEvent(**{k: v for k, v in d.items()
                                        if k in SyncEvent.__dataclass_fields__})
                           for d in data]
        except Exception as e:
            logger.error("fila inválida: %s", e)


# ======================================================================
# Offline Mode
# ======================================================================

class OfflineMode:
    """Opera com último snapshot quando desconectado.

    - update_snapshot: guarda o último snapshot recebido (em disco opcional)
    - read_state: responde de memória/local mesmo offline
    - event_queue: referência à fila do SyncEngine para enfileirar escritas
    """

    def __init__(self, db: SQLiteConnection, sync: SyncEngine) -> None:
        self._db = db
        self._sync = sync
        self._last_snapshot: SyncSnapshot | None = None
        self._snapshot_path: str | None = None

    def save_snapshot(self, snap: SyncSnapshot, path: str | None = None) -> None:
        """Guarda snapshot (em memória e opcionalmente em disco)."""
        self._last_snapshot = snap
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(snap.to_dict(), f, default=str)
            self._snapshot_path = path

    def load_snapshot_from_disk(self, path: str) -> SyncSnapshot | None:
        """Carrega snapshot salvo (para modo offline persistente)."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            snap = SyncSnapshot(**{k: v for k, v in data.items()
                                   if k in SyncSnapshot.__dataclass_fields__})
            self._last_snapshot = snap
            return snap
        except Exception:
            return None

    def read_state(self, table: str, query: str = "",
                   params: tuple = ()) -> list[dict[str, Any]]:
        """Lê estado: do snapshot se offline, do DB se online."""
        if self._last_snapshot and table in self._last_snapshot.tables:
            return self._last_snapshot.tables[table]
        try:
            rows = self._db.fetchall(f"SELECT * FROM {table} {query}", params)
            return [dict(r) for r in rows]
        except Exception:
            return []

    def is_offline(self) -> bool:
        return self._last_snapshot is not None

    def has_snapshot(self) -> bool:
        return self._last_snapshot is not None


# ======================================================================
# Conflict Resolver
# ======================================================================

class ConflictResolver:
    """Política de conflitos: master wins (R12.1 — simplicidade)."""

    def __init__(self, master_id: str) -> None:
        self._master_id = master_id

    def resolve(self, local_node: Node, incoming_node: Node) -> Node:
        """Decide quem tem autoridade: master vence sempre."""
        if incoming_node.role == NodeRole.MASTER:
            return incoming_node
        if local_node.role == NodeRole.MASTER:
            return local_node
        # ambos clientes: mais recente (last_seen)
        if incoming_node.last_seen_s >= local_node.last_seen_s:
            return incoming_node
        return local_node

    def should_apply(self, source_node: Node, is_master_local: bool) -> bool:
        """Se um snapshot pode ser aplicado (master wins)."""
        return source_node.role == NodeRole.MASTER or not is_master_local