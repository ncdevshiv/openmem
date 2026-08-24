"""
Recall-usage tracking for OpenMem.

Records which memories are RETURNED TO AN AGENT by consumption surfaces
(currently the MCP recall()/context()/forget() tools), producing the
fitness signal that pruning/evolution (autonomous/) has so far lacked.

Deliberately NOT recorded inside VectorDB.search(): the retrieval eval,
the learning cycle, and internal consumers all call search(), and folding
their retrievals into the signal would pollute agent-usage evidence with
synthetic queries.

Isolation: OPENMEM_USAGE_DB_PATH overrides the database location (same
convention as OPENMEM_DB_PATH for the vector store). The test suite sets
it so no test ever touches the live data/ tree.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "memory", "usage.db"
)


def _resolve_default_db_path() -> str:
    """Env override → repo-relative default (data/memory/usage.db)."""
    env_path = os.environ.get("OPENMEM_USAGE_DB_PATH")
    if env_path:
        return env_path
    return DEFAULT_DB_PATH


class UsageTracker:
    """
    SQLite-backed record of which memories reach an agent.

    Two tables: an append-only event log (recall_events) for auditing, and
    an aggregate per-memory counter (memory_usage) that scoring code can
    read without scanning events.
    """

    def __init__(self, db_path: str = None):
        self.db_path = os.path.abspath(db_path or _resolve_default_db_path())
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if absent; safe to call on every construction."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recall_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    query TEXT,
                    source TEXT,
                    recorded_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_usage (
                    memory_id TEXT PRIMARY KEY,
                    recall_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    last_query TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_memory "
                "ON recall_events(memory_id)"
            )
            conn.commit()
        finally:
            conn.close()

    def record_events(self, memory_ids: List[str], query: str = "",
                      source: str = "mcp") -> int:
        """
        Record one recall event per memory id (duplicates within a single
        result set are collapsed — a result set cannot return the same
        memory twice).

        Args:
            memory_ids: Memory ids returned by a consumption surface
            query: The query that produced them (truncated to 300 chars)
            source: Surface name, e.g. "mcp.recall"

        Returns:
            Number of events actually written
        """
        seen = []
        for mid in memory_ids or []:
            if mid and mid not in seen:
                seen.append(mid)
        if not seen:
            return 0

        now = datetime.now().isoformat()
        q = (query or "")[:300]
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.executemany(
                    "INSERT INTO recall_events "
                    "(memory_id, query, source, recorded_at) VALUES (?, ?, ?, ?)",
                    [(mid, q, source, now) for mid in seen],
                )
                conn.executemany(
                    "INSERT INTO memory_usage "
                    "(memory_id, recall_count, last_used, last_query) "
                    "VALUES (?, 1, ?, ?) "
                    "ON CONFLICT(memory_id) DO UPDATE SET "
                    "recall_count = recall_count + 1, "
                    "last_used = excluded.last_used, "
                    "last_query = excluded.last_query",
                    [(mid, now, q) for mid in seen],
                )
            return len(seen)
        except sqlite3.Error as e:
            logger.error("[OpenMem] usage record failed: %s", e)
            return 0
        finally:
            conn.close()

    def usage_for(self, memory_id: str) -> Optional[Dict]:
        """Aggregate usage for one memory id, or None when never recalled."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT memory_id, recall_count, last_used, last_query "
                "FROM memory_usage WHERE memory_id = ?", (memory_id,)
            ).fetchone()
            if not row:
                return None
            return {"memory_id": row[0], "recall_count": row[1],
                    "last_used": row[2], "last_query": row[3]}
        finally:
            conn.close()

    def get_usage_counts(self, limit: int = None) -> List[Dict]:
        """
        Per-memory aggregate counts, most-recalled first.

        Args:
            limit: Optional cap on rows returned

        Returns:
            List of {memory_id, recall_count, last_used, last_query}
        """
        sql = ("SELECT memory_id, recall_count, last_used, last_query "
               "FROM memory_usage ORDER BY recall_count DESC, memory_id ASC")
        params: list = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(sql, params).fetchall()
            return [{"memory_id": r[0], "recall_count": r[1],
                     "last_used": r[2], "last_query": r[3]} for r in rows]
        finally:
            conn.close()

    def total_events(self) -> int:
        """Total number of recorded recall events."""
        conn = sqlite3.connect(self.db_path)
        try:
            return int(conn.execute(
                "SELECT COUNT(*) FROM recall_events").fetchone()[0])
        finally:
            conn.close()

    def forget_memory(self, memory_id: str) -> bool:
        """
        Purge all usage data for a deleted memory so aggregates never
        reference ghost ids. Returns True when rows existed.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM recall_events WHERE memory_id = ?", (memory_id,))
                events_deleted = cur.rowcount
                conn.execute(
                    "DELETE FROM memory_usage WHERE memory_id = ?", (memory_id,))
            return events_deleted > 0
        except sqlite3.Error as e:
            logger.error("[OpenMem] usage forget failed: %s", e)
            return False
        finally:
            conn.close()


_tracker_instance: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get or create the process-wide tracker singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = UsageTracker()
    return _tracker_instance


def reset_usage_tracker():
    """Drop the singleton (tests re-point OPENMEM_USAGE_DB_PATH with it)."""
    global _tracker_instance
    _tracker_instance = None
