"""
LanceMem Honcho Integration.
Provides session storage, user representation, and natural language memory queries.
Combines Honcho with LanceDB for hybrid memory management.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("openmem.honcho")


try:
    from honcho import Honcho
    from honcho.types import Message, Peer
    HONCHO_AVAILABLE = True
except ImportError:
    HONCHO_AVAILABLE = False


class LanceHonchoMemory:
    """
    Hybrid Honcho + LanceDB memory layer.
    
    Uses:
    - Honcho for session management and user representation
    - LanceDB for vector search and long-term memory
    
    This gives you the best of both:
    - Honcho's native session/context management
    - LanceDB's fast vector search and scalability
    """

    def __init__(self, workspace_id: str = "lancemem-agent", base_path: str = None):
        self.workspace_id = workspace_id
        self.base_path = base_path or os.path.join(os.path.dirname(__file__), "data", "honcho")
        os.makedirs(self.base_path, exist_ok=True)

        self.honcho = None
        self.user_peer = None
        self.agent_peer = None

        # LanceDB for vector search
        self._vector_db = None

        if HONCHO_AVAILABLE:
            self._init_honcho()
        else:
            print("[LanceHonchoMemory] Honcho not installed. Run: pip install honcho-ai")

        self._init_vector_db()

    def _init_honcho(self):
        """Initialize Honcho client and peers."""
        try:
            self.honcho = Honcho(workspace_id=self.workspace_id)
            self.user_peer = self.honcho.peer("user")
            self.agent_peer = self.honcho.peer("agent")
            print(f"[LanceHonchoMemory] Honcho connected: {self.workspace_id}")
        except Exception as e:
            print(f"[LanceHonchoMemory] Honcho init failed: {e}")
            self.honcho = None

    def _init_vector_db(self):
        """Initialize LanceDB for vector search."""
        try:
            from memory_store.vector_db import get_vector_db
            self._vector_db = get_vector_db()
            print("[LanceHonchoMemory] LanceDB connected")
        except Exception as e:
            print(f"[LanceHonchoMemory] LanceDB init failed: {e}")

    def create_session(self, session_id: str = None, metadata: Dict = None) -> str:
        """Create a new session."""
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if self.honcho:
            try:
                session = self.honcho.session(session_id, metadata=metadata)
                return session.id
            except Exception as e:
                print(f"[LanceHonchoMemory] Session creation failed: {e}")

        return session_id

    def add_message(
        self,
        content: str,
        role: str = "user",
        session_id: str = None,
        metadata: Dict = None
    ):
        """Add a message to the current session."""
        if not session_id:
            session_id = self.workspace_id

        if self.honcho:
            try:
                peer = self.user_peer if role == "user" else self.agent_peer
                message = peer.message(content, metadata=metadata or {})
                session = self.honcho.session(session_id)
                session.add_messages([message])
            except Exception as e:
                print(f"[LanceHonchoMemory] Add message failed: {e}")

        # Also add to LanceDB for vector search
        if self._vector_db:
            self._vector_db.add_memory(
                content=content,
                session_id=session_id,
                importance=0.6 if role == "user" else 0.5,
                metadata={"role": role, **(metadata or {})}
            )

    def add_conversation(
        self,
        messages: List[Dict],
        session_id: str = None
    ):
        """Add a full conversation."""
        if not session_id:
            session_id = self.workspace_id

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})
            self.add_message(content, role, session_id, metadata)

    def query_user(self, query: str) -> str:
        """
        Natural language query about the user.
        Uses Honcho's native query or falls back to LanceDB search.
        """
        if self.honcho and self.user_peer:
            try:
                response = self.user_peer.chat(query)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                print(f"[LanceHonchoMemory] User query failed: {e}")

        # Fallback to LanceDB search
        if self._vector_db:
            profiles = self._vector_db.get_all_user_profiles()
            if query.lower() in profiles:
                return profiles[query.lower()].get("value", "")

        return "[No profile data found]"

    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memories using LanceDB vector search."""
        if self._vector_db:
            try:
                return self._vector_db.search(query, n_results=limit)
            except Exception as e:
                print(f"[LanceHonchoMemory] Search failed: {e}")

        # Fallback to Honcho search
        if self.honcho and self.user_peer:
            try:
                results = self.user_peer.search(query, limit=limit)
                return [
                    {
                        "content": r.content if hasattr(r, 'content') else str(r),
                        "session": getattr(r, 'session_id', 'unknown'),
                        "timestamp": getattr(r, 'created_at', None)
                    }
                    for r in results
                ]
            except Exception as e:
                logger.debug(f"Honcho search failed: {e}")

        return []

    def get_session_context(self, session_id: str = None, tokens: int = 10000) -> str:
        """Get session context for LLM."""
        if not session_id:
            session_id = self.workspace_id

        if self.honcho:
            try:
                session = self.honcho.session(session_id)
                context = session.context(summary=True, tokens=tokens)
                return str(context)
            except Exception as e:
                print(f"[LanceHonchoMemory] Context retrieval failed: {e}")

        # Fallback: collect from LanceDB
        if self._vector_db:
            recent = self._vector_db.get_recent_memories(hours=24, limit=20)
            context_parts = []
            for r in recent:
                role = r.get("metadata", {}).get("role", "unknown")
                content = r.get("content", "")
                context_parts.append(f"{role}: {content}")
            return "\n".join(context_parts)

        return ""

    def get_user_representation(self, session_id: str = None) -> Dict:
        """Get learned representation of the user."""
        if self.honcho and self.user_peer:
            try:
                if not session_id:
                    session_id = self.workspace_id
                session = self.honcho.session(session_id)
                representation = session.representation(self.user_peer)
                return {
                    "user_id": str(self.user_peer.id),
                    "representation": str(representation) if representation else None,
                    "workspace": self.workspace_id,
                    "backend": "honcho"
                }
            except Exception as e:
                return {"error": str(e), "backend": "honcho"}

        return {"error": "No backend available", "backend": "none"}

    def get_all_sessions(self) -> List[str]:
        """Get list of all session IDs."""
        if self.honcho:
            try:
                sessions = self.honcho.session.list()
                return [s.id for s in sessions]
            except Exception as e:
                logger.debug(f"Honcho session list failed: {e}")

        return []

    def get_stats(self) -> Dict:
        """Get memory system statistics."""
        return {
            "honcho_available": HONCHO_AVAILABLE and self.honcho is not None,
            "lancedb_available": self._vector_db is not None,
            "workspace_id": self.workspace_id,
            "user_peer": str(self.user_peer.id) if self.user_peer else None,
            "sessions_count": len(self.get_all_sessions()),
            "memory_count": len(self._vector_db) if self._vector_db else 0,
            "backends": ["honcho", "lancedb"] if self.honcho and self._vector_db else ["lancedb"]
        }


# Alias for backwards compatibility
HonchoMemory = LanceHonchoMemory

# Singleton
_honcho_instance = None

def get_honcho_memory() -> LanceHonchoMemory:
    """Get or create singleton HonchoMemory instance."""
    global _honcho_instance
    if _honcho_instance is None:
        _honcho_instance = LanceHonchoMemory()
    return _honcho_instance
