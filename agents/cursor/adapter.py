"""
OpenMem — Cursor Editor Adapter.

Session storage: ~/.cursor/sessions/ or .cursor/ in workspace
Skill install: .cursor/rules/ or ~/.cursor/skills/
Context injection: .cursor/rules/memory.md (Cursor reads rules dir for context)
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from ..base import AgentAdapter, register_adapter


class CursorAdapter(AgentAdapter):
    """Cursor editor specific adapter."""

    AGENT_NAME = "Cursor"
    SKILL_FILES = ["SKILL.md", "learner.py"]

    def __init__(self):
        self._workspace = os.environ.get("CURSOR_WORKSPACE", os.getcwd())
        self._cursor_dir = os.path.join(os.path.expanduser("~"), ".cursor")
        self._session_dir = os.path.join(self._cursor_dir, "sessions")
        os.makedirs(self._session_dir, exist_ok=True)
        self._message_hook = None

    def get_session_messages(self, limit: int = 100) -> List[Dict[str, str]]:
        messages = []
        # Check workspace-level .cursor/ first
        workspace_cursor = os.path.join(self._workspace, ".cursor")
        for session_dir in [workspace_cursor, self._session_dir]:
            if not os.path.isdir(session_dir):
                continue
            for fpath in sorted(
                self.find_session_files(session_dir, "*.json", hours_back=168),
                key=lambda f: os.path.getmtime(f), reverse=True
            ):
                data = self.load_session_json(fpath)
                if not data:
                    continue
                for msg in data.get("messages", data.get("conversation", [])):
                    if isinstance(msg, dict) and "content" in msg:
                        messages.append({
                            "role": msg.get("role", "unknown"),
                            "content": msg["content"],
                            "timestamp": msg.get("timestamp", ""),
                        })
                if len(messages) >= limit:
                    break
            if messages:
                break
        return messages[:limit]

    def inject_context(self, context: str) -> bool:
        """
        Inject into Cursor's rules directory.
        Cursor automatically reads .cursor/rules/ files for system context.
        """
        try:
            # Primary: .cursor/rules/memory.md
            rules_dir = os.path.join(self._workspace, ".cursor", "rules")
            os.makedirs(rules_dir, exist_ok=True)
            rules_file = os.path.join(rules_dir, "memory.md")
            with open(rules_file, "w", encoding="utf-8") as f:
                f.write(f"# OpenMem Memory Context\n\n{context}\n")
            return True
        except OSError:
            return False

    def get_workspace_path(self) -> str:
        return os.path.abspath(self._workspace)

    def get_session_id(self) -> str:
        for session_dir in [
            os.path.join(self._workspace, ".cursor"),
            self._session_dir
        ]:
            if os.path.isdir(session_dir):
                files = self.find_session_files(session_dir, "*.json", hours_back=24)
                if files:
                    return Path(max(files, key=lambda f: os.path.getmtime(f))).stem
        return f"cursor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def get_agent_name(self) -> str:
        return self.AGENT_NAME

    def get_skill_install_path(self) -> Optional[str]:
        return os.path.join(self._workspace, ".cursor", "rules")

    def register_message_hook(self, callback: Callable[[Dict], None]) -> bool:
        self._message_hook = callback
        return True


register_adapter("cursor", CursorAdapter)
