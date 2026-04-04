"""
OpenMem — OpenClaw Adapter.

Session storage: ~/.openclaw/sessions/ or workspace memory/
Skill install: ~/.openclaw/skills/lancemem/
Context injection: learner.py command interface
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from ..base import AgentAdapter, register_adapter


class OpenclawAdapter(AgentAdapter):
    """OpenClaw specific adapter."""

    AGENT_NAME = "OpenClaw"
    SKILL_FILES = ["SKILL.md", "learner.py", "manifest.json"]

    def __init__(self):
        self._workspace = os.getcwd()
        self._openclaw_dir = os.path.join(os.path.expanduser("~"), ".openclaw")
        self._session_dir = os.path.join(self._openclaw_dir, "sessions")
        self._memory_dir = os.path.join(self._workspace, "memory")
        for d in [self._session_dir, self._memory_dir]:
            os.makedirs(d, exist_ok=True)
        self._message_hook = None

    def get_session_messages(self, limit: int = 100) -> List[Dict[str, str]]:
        messages = []
        for session_dir in [self._session_dir, self._memory_dir]:
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
                            "role": msg.get("role", msg.get("sender", "unknown")),
                            "content": msg["content"],
                            "timestamp": msg.get("timestamp", ""),
                        })
                if len(messages) >= limit:
                    break
            if messages:
                break
        return messages[:limit]

    def inject_context(self, context: str) -> bool:
        try:
            ctx_file = os.path.join(self._openclaw_dir, "memory_context.md")
            with open(ctx_file, "w", encoding="utf-8") as f:
                f.write(f"# OpenMem Memory Context\n\n{context}\n")
            return True
        except OSError:
            return False

    def get_workspace_path(self) -> str:
        return os.path.abspath(self._workspace)

    def get_session_id(self) -> str:
        for session_dir in [self._session_dir, self._memory_dir]:
            if os.path.isdir(session_dir):
                files = self.find_session_files(session_dir, "*.json", hours_back=24)
                if files:
                    return Path(max(files, key=lambda f: os.path.getmtime(f))).stem
        return f"openclaw_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def get_agent_name(self) -> str:
        return self.AGENT_NAME

    def get_skill_install_path(self) -> Optional[str]:
        return os.path.join(self._openclaw_dir, "skills", "lancemem")

    def register_message_hook(self, callback: Callable[[Dict], None]) -> bool:
        self._message_hook = callback
        return True

    def get_config(self) -> Dict:
        """Load OpenClaw config if available."""
        config_path = os.path.join(self._openclaw_dir, "config.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}


register_adapter("openclaw", OpenclawAdapter)
