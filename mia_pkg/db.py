"""Camada de persistência SQLite — conexão, WAL mode, schema init, rows como dict."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SQLiteConnection:
    """Gerencia conexão SQLite com WAL mode e inicialização de schema."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Abre a conexão e configura WAL mode + row_factory = dict."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        """Fecha a conexão graceful."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Banco não conectado. Chame connect() primeiro.")
        return self._conn

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Cria todas as tabelas do schema v1 conforme especificação F.2."""
        c = self.connection
        c.executescript(_SCHEMA_SQL)
        c.execute("PRAGMA user_version = 1")
        c.commit()

    def get_schema_version(self) -> int:
        cur = self.connection.execute("PRAGMA user_version")
        return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Executa SQL e retorna cursor."""
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        """Executa SQL em lote."""
        return self.connection.executemany(sql, params)

    def commit(self) -> None:
        self.connection.commit()

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Retorna uma linha como dict ou None."""
        row = self.connection.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Retorna todas as linhas como lista de dicts."""
        return [dict(r) for r in self.connection.execute(sql, params).fetchall()]


# ======================================================================
# Schema SQL — seção F.2 da especificação
# ======================================================================

_SCHEMA_SQL = """
-- memory_objects
CREATE TABLE IF NOT EXISTS memory_objects (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('experience','preference','fact','belief','emotion','relationship','decision')),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5 CHECK(importance BETWEEN 0.0 AND 1.0),
    confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence BETWEEN 0.0 AND 1.0),
    scope TEXT NOT NULL DEFAULT 'personal' CHECK(scope IN ('personal','shared','private')),
    person_id TEXT REFERENCES people(id),
    embedding BLOB,
    emotional_context TEXT,
    provenance TEXT,
    decay_state TEXT DEFAULT 'active',
    status TEXT DEFAULT 'active',
    revision_history TEXT,
    observed_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    is_consolidated INTEGER NOT NULL DEFAULT 0,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TEXT,
    tags TEXT DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_objects(type);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_objects(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_objects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_person ON memory_objects(person_id);

-- memory_associations
CREATE TABLE IF NOT EXISTS memory_associations (
    memory_id TEXT NOT NULL REFERENCES memory_objects(id),
    associated_id TEXT NOT NULL REFERENCES memory_objects(id),
    strength REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    PRIMARY KEY (memory_id, associated_id)
);

-- beliefs (§21 onboarding v2)
CREATE TABLE IF NOT EXISTS beliefs (
    id TEXT PRIMARY KEY,
    proposition TEXT NOT NULL,
    confidence REAL DEFAULT 0.5 CHECK(confidence BETWEEN 0.0 AND 1.0),
    source_evidence TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    revision_history TEXT,
    person_id TEXT REFERENCES people(id)
);

-- needs (§16 onboarding v2)
CREATE TABLE IF NOT EXISTS needs (
    id TEXT PRIMARY KEY,
    need_type TEXT NOT NULL,
    intensity REAL DEFAULT 0.5 CHECK(intensity BETWEEN 0.0 AND 1.0),
    satisfied INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_fulfilled_at TEXT,
    person_id TEXT REFERENCES people(id)
);

-- desires (§16 onboarding v2)
CREATE TABLE IF NOT EXISTS desires (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    desire_type TEXT,
    priority REAL DEFAULT 0.5 CHECK(priority BETWEEN 0.0 AND 1.0),
    fulfilled INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    goal_id TEXT REFERENCES goals(id),
    person_id TEXT REFERENCES people(id)
);

-- attention_log (§26 onboarding v2)
CREATE TABLE IF NOT EXISTS attention_log (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_id TEXT,
    decision TEXT NOT NULL,
    relevance REAL,
    urgency REAL,
    importance REAL,
    reasoning TEXT,
    created_at TEXT NOT NULL
);

-- events
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);

-- state_transitions_audit (append-only)
CREATE TABLE IF NOT EXISTS state_transitions_audit (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    component_origin TEXT NOT NULL,
    transition_type TEXT NOT NULL,
    target TEXT NOT NULL,
    key TEXT NOT NULL,
    before_snapshot TEXT NOT NULL,
    after_snapshot TEXT NOT NULL,
    evidence TEXT,
    confidence REAL CHECK(confidence BETWEEN 0.0 AND 1.0),
    applied_by TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    hash TEXT,
    hash_prev TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON state_transitions_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_target ON state_transitions_audit(target);

-- people
CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT,
    metadata TEXT DEFAULT '{}'
);

-- relationships
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES people(id),
    trust REAL NOT NULL DEFAULT 0.5 CHECK(trust BETWEEN 0.0 AND 1.0),
    intimacy REAL NOT NULL DEFAULT 0.0 CHECK(intimacy BETWEEN 0.0 AND 1.0),
    affinity REAL NOT NULL DEFAULT 0.5 CHECK(affinity BETWEEN 0.0 AND 1.0),
    familiarity REAL NOT NULL DEFAULT 0.0 CHECK(familiarity BETWEEN 0.0 AND 1.0),
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_interaction TEXT,
    version INTEGER NOT NULL DEFAULT 1
);

-- relationship_events
CREATE TABLE IF NOT EXISTS relationship_events (
    id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL REFERENCES relationships(id),
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT,
    impact REAL CHECK(impact BETWEEN -1.0 AND 1.0)
);
CREATE INDEX IF NOT EXISTS idx_rel_events_rel ON relationship_events(relationship_id);

-- identity_state
CREATE TABLE IF NOT EXISTS identity_state (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    self_model TEXT NOT NULL,
    core_values TEXT NOT NULL,
    version INTEGER NOT NULL,
    snapshot_at TEXT NOT NULL,
    previous_version TEXT
);

-- personality_state
CREATE TABLE IF NOT EXISTS personality_state (
    id TEXT PRIMARY KEY,
    openness REAL NOT NULL DEFAULT 0.5 CHECK(openness BETWEEN 0.0 AND 1.0),
    conscientiousness REAL NOT NULL DEFAULT 0.5 CHECK(conscientiousness BETWEEN 0.0 AND 1.0),
    extraversion REAL NOT NULL DEFAULT 0.5 CHECK(extraversion BETWEEN 0.0 AND 1.0),
    agreeableness REAL NOT NULL DEFAULT 0.5 CHECK(agreeableness BETWEEN 0.0 AND 1.0),
    neuroticism REAL NOT NULL DEFAULT 0.5 CHECK(neuroticism BETWEEN 0.0 AND 1.0),
    curiosity REAL NOT NULL DEFAULT 0.5 CHECK(curiosity BETWEEN 0.0 AND 1.0),
    playfulness REAL NOT NULL DEFAULT 0.5 CHECK(playfulness BETWEEN 0.0 AND 1.0),
    assertiveness REAL NOT NULL DEFAULT 0.5 CHECK(assertiveness BETWEEN 0.0 AND 1.0),
    empathy REAL NOT NULL DEFAULT 0.5 CHECK(empathy BETWEEN 0.0 AND 1.0),
    independence REAL NOT NULL DEFAULT 0.5 CHECK(independence BETWEEN 0.0 AND 1.0),
    version INTEGER NOT NULL DEFAULT 1,
    snapshot_at TEXT NOT NULL
);

-- emotion_state
CREATE TABLE IF NOT EXISTS emotion_state (
    id TEXT PRIMARY KEY,
    happiness REAL NOT NULL DEFAULT 0.5 CHECK(happiness BETWEEN 0.0 AND 1.0),
    sadness REAL NOT NULL DEFAULT 0.0 CHECK(sadness BETWEEN 0.0 AND 1.0),
    anger REAL NOT NULL DEFAULT 0.0 CHECK(anger BETWEEN 0.0 AND 1.0),
    fear REAL NOT NULL DEFAULT 0.0 CHECK(fear BETWEEN 0.0 AND 1.0),
    surprise REAL NOT NULL DEFAULT 0.0 CHECK(surprise BETWEEN 0.0 AND 1.0),
    disgust REAL NOT NULL DEFAULT 0.0 CHECK(disgust BETWEEN 0.0 AND 1.0),
    trust_level REAL NOT NULL DEFAULT 0.5 CHECK(trust_level BETWEEN 0.0 AND 1.0),
    anticipation REAL NOT NULL DEFAULT 0.5 CHECK(anticipation BETWEEN 0.0 AND 1.0),
    curiosity_level REAL NOT NULL DEFAULT 0.5 CHECK(curiosity_level BETWEEN 0.0 AND 1.0),
    loneliness REAL NOT NULL DEFAULT 0.0 CHECK(loneliness BETWEEN 0.0 AND 1.0),
    affection REAL NOT NULL DEFAULT 0.5 CHECK(affection BETWEEN 0.0 AND 1.0),
    boredom REAL NOT NULL DEFAULT 0.0 CHECK(boredom BETWEEN 0.0 AND 1.0),
    mood_valence REAL NOT NULL DEFAULT 0.0 CHECK(mood_valence BETWEEN -1.0 AND 1.0),
    mood_arousal REAL NOT NULL DEFAULT 0.5 CHECK(mood_arousal BETWEEN 0.0 AND 1.0),
    mood_dominance REAL NOT NULL DEFAULT 0.5 CHECK(mood_dominance BETWEEN 0.0 AND 1.0),
    snapshot_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);

-- sensations
CREATE TABLE IF NOT EXISTS sensations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    valence REAL CHECK(valence BETWEEN -1.0 AND 1.0),
    intensity REAL CHECK(intensity BETWEEN 0.0 AND 1.0),
    possible_causes TEXT DEFAULT '[]',
    detected_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolution TEXT
);

-- diary
CREATE TABLE IF NOT EXISTS diary (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    entry_type TEXT NOT NULL CHECK(entry_type IN ('moment','summary','reflection')),
    content TEXT NOT NULL,
    emotion_snapshot TEXT,
    created_at TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_diary_date ON diary(date DESC);

-- goals
CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','completed','abandoned','paused')),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    deadline TEXT,
    progress REAL NOT NULL DEFAULT 0.0 CHECK(progress BETWEEN 0.0 AND 1.0)
);

-- sessions (existente, mantida)
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    role TEXT
);

-- messages (existente, mantida)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""
