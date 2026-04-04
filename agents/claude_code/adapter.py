"""
OpenMem — Claude Code Adapter (Anthropic Claude CLI).

Session storage: ~/.claude/sessions/ or project-level .claude/
Skill install: ~/.claude/skills/
Context injection: CLAUDE.md system prompt file
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from ..base import AgentAdapter, register_adapter


class ClaudeCodeAdapter(AgentAdapter):
    """Claude Code specific adapter."""

    AGENT_NAME = "Claude Code"
    SKILL_FILES = ["SKILL.md", "learner.py"]

    def __init__(self):
        self._workspace = os.getcwd()
        self._claude_dir = os.path.join(os.path.expanduser("~"), ".claude")
        self._session_dir = os.path.join(self._claude_dir, "sessions")
        os.makedirs(self._session_dir, exist_ok=True)
        self._message_hook = None

    def get_session_messages(self, limit: int = 100) -> List[Dict[str, str]]:
        """Read from Claude session files or CLAUDE.md transcripts."""
        messages = []
        if not os.path.isdir(self._session_dir):
            return messages

        session_files = self.find_session_files(self._session_dir, "*.json", hours_back=168)
        for fpath in sorted(session_files, key=lambda f: os.path.getmtime(f), reverse=True):
            data = self.load_session_json(fpath)
            if not data:
                continue
            msg_list = data.get("messages", [])
            for msg in msg_list:
                if isinstance(msg, dict):
                    messages.append({
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", msg.get("text", "")),
                        "timestamp": msg.get("timestamp", ""),
                    })
            if len(messages) >= limit:
                break
        return messages[:limit]

    def inject_context(self, context: str) -> bool:
        """Inject via CLAUDE.md in workspace root."""
        try:
            claude_md = os.path.join(self._workspace, "CLAUDE.md")
            marker = "## Memory Context"
            if os.path.exists(claude_md):
                with open(claude_md, "r", encoding="utf-8") as f:
                    content = f.read()
                if marker in content:
                    parts = content.split(marker, 1)
                    rest = parts[1].split("\n## ", 1)
                    content = parts[0] + marker + "\n\n" + context + (
                        "\n\n## " + rest[1] if len(rest) > 1 else "\n"
                    )
                else:
                    content += f"\n{marker}\n\n{context}\n"
                with open(claude_md, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(claude_md, "w", encoding="utf-8") as f:
                    f.write(f"# Claude Code Project Context\n\n{marker}\n\n{context}\n")
            return True
        except OSError:
            return False

    def get_workspace_path(self) -> str:
        return os.path.abspath(self._workspace)

    def get_session_id(self) -> str:
        if os.path.isdir(self._session_dir):
            files = self.find_session_files(self._session_dir, "*.json", hours_back=24)
            if files:
                return Path(max(files, key=lambda f: os.path.getmtime(f))).stem
        return f"claude_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def get_agent_name(self) -> str:
        return self.AGENT_NAME

    def get_skill_install_path(self) -> Optional[str]:
        return os.path.join(self._claude_dir, "skills", "memory")

    def register_message_hook(self, callback: Callable[[Dict], None]) -> bool:
        self._message_hook = callback
        return True


register_adapter("claude_code", ClaudeCodeAdapter)
register_adapter("claude", ClaudeCodeAdapter)
