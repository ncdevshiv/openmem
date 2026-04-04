"""
Conversation Indexer for OpenMem.
Indexes OpenClaw session transcripts into the vector database.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from memory_store import get_vector_db


class ConversationIndexer:
    """
    Indexes OpenClaw session conversations into the vector database.
    
    Handles:
    - Reading session transcripts from OpenClaw workspace
    - Parsing and segmenting conversations
    - Extracting metadata (timestamps, channels, sender)
    - Storing in vector DB with importance scoring
    """
    
    def __init__(self, openclaw_workspace: str = None):
        self.vector_db = get_vector_db()
        
        # OpenClaw workspace paths
        self.workspace = openclaw_workspace or os.path.join(
            os.path.expanduser("~"), ".openclaw", "workspace"
        )
        self.sessions_dir = os.path.join(self.workspace, "sessions")
        self.memory_dir = os.path.join(self.workspace, "memory")
        
        # Create dirs if they don't exist
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Index tracking
        self.index_state_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "sessions", "index_state.json"
        )
        os.makedirs(os.path.dirname(os.path.abspath(self.index_state_file)), exist_ok=True)
        self.index_state = self._load_index_state()
    
    def _load_index_state(self) -> Dict:
        """Load the indexing state (last indexed sessions)."""
        if os.path.exists(self.index_state_file):
            with open(self.index_state_file, 'r') as f:
                return json.load(f)
        return {
            "indexed_sessions": [],  # List of session IDs already indexed
            "last_index_run": None,
            "total_messages_indexed": 0
        }
    
    def _save_index_state(self):
        """Save indexing state."""
        self.index_state["last_index_run"] = datetime.now().isoformat()
        with open(self.index_state_file, 'w') as f:
            json.dump(self.index_state, f, indent=2)
    
    def get_openclaw_sessions(self, hours_back: int = 24) -> List[Dict]:
        """
        Get list of OpenClaw sessions from the last N hours.
        Returns list of session info dicts.
        """
        sessions = []
        
        # Try to read from sessions directory
        if os.path.exists(self.sessions_dir):
            for session_file in Path(self.sessions_dir).glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # Get last modified time
                    mtime = datetime.fromtimestamp(os.path.getmtime(session_file))
                    
                    # Filter by hours
                    if (datetime.now() - mtime).total_seconds() / 3600 <= hours_back:
                        sessions.append({
                            "id": session_file.stem,
                            "path": str(session_file),
                            "last_modified": mtime.isoformat(),
                            "data": session_data
                        })
                except Exception as e:
                    print(f"[Indexer] Error reading {session_file}: {e}")
        
        # Also check OpenClaw's own session storage
        openclaw_sessions = os.path.join(
            os.path.expanduser("~"), ".openclaw", "sessions"
        )
        if os.path.exists(openclaw_sessions):
            for session_file in Path(openclaw_sessions).glob("*.json"):
                if session_file.stem in self.index_state.get("indexed_sessions", []):
                    continue  # Already indexed
                
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    mtime = datetime.fromtimestamp(os.path.getmtime(session_file))
                    
                    if (datetime.now() - mtime).total_seconds() / 3600 <= hours_back:
                        sessions.append({
                            "id": session_file.stem,
                            "path": str(session_file),
                            "last_modified": mtime.isoformat(),
                            "data": session_data
                        })
                except Exception as e:
                    print(f"[Indexer] Error reading {session_file}: {e}")
        
        return sessions
    
    def parse_session_messages(self, session_data: Dict) -> List[Dict]:
        """
        Parse session data into individual messages.
        Returns list of message dicts with metadata.
        """
        messages = []
        
        # Handle various session formats
        if "messages" in session_data:
            msg_list = session_data["messages"]
        elif isinstance(session_data, list):
            msg_list = session_data
        else:
            # Try to find messages in unknown format
            return []
        
        for i, msg in enumerate(msg_list):
            if isinstance(msg, dict):
                parsed = {
                    "id": msg.get("id", f"msg_{i}"),
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp", msg.get("created_at", "")),
                    "channel": msg.get("channel", session_data.get("channel", "unknown")),
                    "session_id": session_data.get("id", "unknown")
                }
                
                # Handle nested content
                if isinstance(parsed["content"], list):
                    parsed["content"] = " ".join([
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in parsed["content"]
                    ])
                elif not isinstance(parsed["content"], str):
                    parsed["content"] = str(parsed["content"])
                
                messages.append(parsed)
        
        return messages
    
    def score_message_importance(self, message: Dict) -> float:
        """
        Score a message's importance (0.0 to 1.0).
        
        Factors:
        - Has user confirmed something important
        - Contains a decision or commitment
        - Contains new user information
        - Message from assistant with successful outcome
        """
        content = message.get("content", "").lower()
        role = message.get("role", "")
        
        importance = 0.5  # Base importance
        
        # High importance indicators
        if any(kw in content for kw in [
            "remember", "important", "don't forget", "remind me",
            "my name is", "i'm working on", "preference", "always"
        ]):
            importance += 0.2
        
        # Decision/commitment indicators
        if any(kw in content for kw in [
            "decided", "going to", "will use", "should",
            "plan is", "let's go with"
        ]):
            importance += 0.15
        
        # Success confirmation
        if any(kw in content for kw in ["perfect", "thanks", "great", "works", "awesome"]):
            importance += 0.1
        
        # User messages are slightly more important
        if role == "user":
            importance += 0.05
        
        # Very long messages might be context-rich
        if len(content) > 500:
            importance += 0.05
        
        # Cap at 1.0
        return min(1.0, importance)
    
    def extract_tags(self, message: Dict) -> List[str]:
        """Extract tags from message content."""
        content = message.get("content", "").lower()
        tags = []
        
        # Topic tags
        topic_keywords = {
            "coding": ["code", "function", "script", "debug", "api", "python", "javascript"],
            "ai": ["ai", "model", "llm", "gpt", "hermes", "agent"],
            "project": ["project", "building", "creating", "working on"],
            "help": ["help", "how to", "can you", "need to"],
            "question": ["what", "why", "how", "when", "where", "?"],
            "memory": ["remember", "forget", "recall", "remind"],
            "tool": ["search", "browse", "run", "execute", "create"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in content for kw in keywords):
                tags.append(topic)
        
        # Channel tag
        channel = message.get("channel", "unknown")
        if channel != "unknown":
            tags.append(f"channel:{channel}")
        
        return tags
    
    def index_session(self, session: Dict) -> int:
        """
        Index a single session's messages into the vector DB.
        Returns number of messages indexed.
        """
        session_id = session["id"]
        session_data = session.get("data", {})
        
        # Skip if already indexed
        if session_id in self.index_state.get("indexed_sessions", []):
            return 0
        
        messages = self.parse_session_messages(session_data)
        
        indexed_count = 0
        for msg in messages:
            if not msg.get("content") or len(msg["content"]) < 10:
                continue  # Skip very short messages
            
            importance = self.score_message_importance(msg)
            tags = self.extract_tags(msg)
            
            self.vector_db.add_memory(
                content=msg["content"],
                session_id=session_id,
                importance=importance,
                tags=tags,
                metadata={
                    "role": msg.get("role"),
                    "channel": msg.get("channel"),
                    "timestamp": msg.get("timestamp")
                }
            )
            indexed_count += 1
        
        # Mark as indexed
        if indexed_count > 0:
            self.index_state["indexed_sessions"].append(session_id)
            self.index_state["total_messages_indexed"] += indexed_count
        
        return indexed_count
    
    def run_indexing(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Run full indexing cycle on recent sessions.
        Returns indexing report.
        """
        report = {
            "sessions_found": 0,
            "sessions_indexed": 0,
            "messages_indexed": 0,
            "errors": []
        }
        
        sessions = self.get_openclaw_sessions(hours_back=hours_back)
        report["sessions_found"] = len(sessions)
        
        for session in sessions:
            try:
                count = self.index_session(session)
                if count > 0:
                    report["sessions_indexed"] += 1
                    report["messages_indexed"] += count
            except Exception as e:
                report["errors"].append({
                    "session_id": session.get("id"),
                    "error": str(e)
                })
        
        self._save_index_state()
        
        return report
    
    def reindex_all(self) -> Dict[str, Any]:
        """
        Re-index all sessions from scratch.
        WARNING: Resets index state.
        """
        self.index_state = {
            "indexed_sessions": [],
            "last_index_run": None,
            "total_messages_indexed": 0
        }
        self._save_index_state()
        
        return self.run_indexing(hours_back=24 * 30)  # Last 30 days
    
    def get_stats(self) -> Dict:
        """Get indexing statistics."""
        return {
            "index_state": {
                "total_indexed": len(self.index_state.get("indexed_sessions", [])),
                "total_messages": self.index_state.get("total_messages_indexed", 0),
                "last_run": self.index_state.get("last_index_run")
            },
            "vector_db_stats": self.vector_db.get_stats()
        }
