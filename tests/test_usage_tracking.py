"""
Tests for recall-usage tracking (memory_store/usage_tracker.py).

Covers the tracker API directly (temp SQLite via constructor DI) and the
end-to-end producer path through the real MCP server subprocess: remember
→ recall/context must leave events in the OPENMEM_USAGE_DB_PATH database,
and forget() must purge them along with the memory.

No test touches the live data/ tree: unit tests inject paths, the
protocol test points both OPENMEM_DB_PATH and OPENMEM_USAGE_DB_PATH at a
fresh temp dir.
"""

import os
import sys
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


class TestUsageTracker(unittest.TestCase):
    """Direct API tests against an injected temp SQLite file."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="openmem_usage_test_")
        self.db_path = os.path.join(self.test_dir, "usage.db")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _tracker(self):
        from memory_store.usage_tracker import UsageTracker
        return UsageTracker(db_path=self.db_path)

    def test_record_and_read_counts(self):
        tracker = self._tracker()
        written = tracker.record_events(["m1", "m2"], query="q", source="test")
        self.assertEqual(written, 2)
        self.assertEqual(tracker.total_events(), 2)

        u1 = tracker.usage_for("m1")
        self.assertEqual(u1["recall_count"], 1)
        self.assertEqual(u1["last_query"], "q")
        self.assertIsNone(tracker.usage_for("never-recorded"))

    def test_duplicates_within_call_collapse(self):
        tracker = self._tracker()
        # A single result set cannot return one memory twice.
        written = tracker.record_events(["m1", "m1", ""], query="q")
        self.assertEqual(written, 1)
        self.assertEqual(tracker.usage_for("m1")["recall_count"], 1)

    def test_empty_ids_write_nothing(self):
        tracker = self._tracker()
        self.assertEqual(tracker.record_events([]), 0)
        self.assertEqual(tracker.record_events([None, "", "  ".strip()] or []), 0)
        self.assertEqual(tracker.total_events(), 0)

    def test_repeated_recalls_accumulate(self):
        tracker = self._tracker()
        tracker.record_events(["m1"], query="first")
        tracker.record_events(["m1", "m2"], query="second")
        self.assertEqual(tracker.usage_for("m1")["recall_count"], 2)
        self.assertEqual(tracker.usage_for("m1")["last_query"], "second")
        self.assertEqual(tracker.total_events(), 3)

    def test_counts_persist_across_instances(self):
        self._tracker().record_events(["m1"], query="q")
        reopened = self._tracker()
        self.assertEqual(reopened.usage_for("m1")["recall_count"], 1)

    def test_get_usage_counts_ordered_desc(self):
        tracker = self._tracker()
        for _ in range(3):
            tracker.record_events(["hot"])
        tracker.record_events(["cold"])
        counts = tracker.get_usage_counts()
        self.assertEqual([c["memory_id"] for c in counts], ["hot", "cold"])
        limited = tracker.get_usage_counts(limit=1)
        self.assertEqual(len(limited), 1)
        self.assertEqual(limited[0]["memory_id"], "hot")

    def test_forget_memory_purges_rows(self):
        tracker = self._tracker()
        tracker.record_events(["gone", "kept"], query="q")
        self.assertTrue(tracker.forget_memory("gone"))
        self.assertIsNone(tracker.usage_for("gone"))
        self.assertFalse(tracker.forget_memory("gone"))  # nothing left
        self.assertEqual(tracker.total_events(), 1)
        self.assertIsNotNone(tracker.usage_for("kept"))

    def test_long_queries_truncated(self):
        tracker = self._tracker()
        tracker.record_events(["m1"], query="x" * 1000)
        self.assertEqual(len(tracker.usage_for("m1")["last_query"]), 300)


class TestMcpUsageRecording(unittest.TestCase):
    """
    End-to-end: drive the real MCP server over stdio against isolated
    stores, then inspect the usage database the tools were told to write.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="openmem_usage_e2e_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _server_params(self):
        from mcp import StdioServerParameters
        env = dict(os.environ)
        env["OPENMEM_DB_PATH"] = os.path.join(self.test_dir, "lancedb")
        env["OPENMEM_USAGE_DB_PATH"] = os.path.join(self.test_dir, "usage.db")
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server"],
            cwd=str(REPO_ROOT),
            env=env,
        )

    def with_session(self, coro_fn):
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        async def _runner():
            async with stdio_client(self._server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await coro_fn(session)

        return asyncio_run(_runner())

    def test_recall_and_context_record_and_forget_purges(self):
        marker = "usability testing fixture for recall usage tracking"

        def body(session):
            async def run():
                remembered = await session.call_tool(
                    "remember", {"content": marker, "importance": 0.9},
                )
                memory_id = call_first_text(remembered)

                recalled = await session.call_tool(
                    "recall", {"query": "recall usage tracking fixture"})
                ctx = await session.call_tool(
                    "context", {"query": "recall usage tracking fixture"})
                stats_text = await session.call_tool("stats", {})
                forgotten = await session.call_tool(
                    "forget", {"memory_id": memory_id})
                return memory_id, call_first_text(recalled), \
                    call_first_text(ctx), call_first_text(stats_text), \
                    call_first_text(forgotten)

            return run()

        memory_id, recalled, ctx, stats_text, forgotten = \
            self.with_session(body)

        self.assertIn(memory_id, recalled)
        self.assertIn(marker[:80], ctx)

        # stats was captured BEFORE forget: both consumption surfaces must
        # have recorded events by then.
        payload = json.loads(stats_text)
        self.assertGreaterEqual(
            payload.get("total_recall_events"), 2,
            "recall+context must each record events")

        # forget() purges every usage row referencing the deleted id
        self.assertEqual(forgotten.strip().lower(), "true")
        usage_db = os.path.join(self.test_dir, "usage.db")
        conn = sqlite3.connect(usage_db)
        try:
            ghost_events = conn.execute(
                "SELECT COUNT(*) FROM recall_events WHERE memory_id = ?",
                (memory_id,)).fetchone()[0]
            ghost_agg = conn.execute(
                "SELECT COUNT(*) FROM memory_usage WHERE memory_id = ?",
                (memory_id,)).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(ghost_events, 0)
        self.assertEqual(ghost_agg, 0)


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


def call_first_text(result) -> str:
    for block in result.content:
        if getattr(block, "text", None) is not None:
            return block.text
    return ""


if __name__ == "__main__":
    unittest.main()
