"""
LanceMem Vector DB - Powered by LanceDB.
High-performance vector database for autonomous agent memory.
"""

import os
import json
import uuid
import hashlib
import logging
import traceback
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

# Module logger
logger = logging.getLogger("openmem.vector_db")

try:
    import lancedb
    from lancedb.embeddings import EmbeddingFunction
    from lancedb.table import Table
    import pyarrow as pa
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False


@dataclass
class Memory:
    """A single memory entry."""
    id: str
    content: str
    session_id: Optional[str]
    timestamp: str
    importance: float
    tags: List[str]
    metadata: Dict[str, Any]
    vector: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata
        }


class LanceDBVectorStore:
    """
    LanceDB-backed vector store for semantic memory search.
    
    Features:
    - Sub-millisecond vector search
    - Built-in versioning
    - Schema evolution (add columns anytime)
    - Cloud-native storage (S3, GCS, etc.)
    - Automatic index optimization
    - ACID transactions
    """

    # LanceDB Table Schema (PyArrow)
    SCHEMA = pa.schema([
        pa.field("id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("session_id", pa.string(), nullable=True),
        pa.field("timestamp", pa.string()),
        pa.field("importance", pa.float32()),
        pa.field("tags", pa.list_(pa.string())),
        pa.field("metadata", pa.string()),  # JSON serialized
        pa.field("vector", pa.list_(pa.float32()), nullable=True),
    ])

    # Index configuration for optimized search
    INDEX_CONFIG = {
        "num_sub_vectors": 96,  # For HNSW
        "distance_type": "cosine",  # or "l2", "dot"
    }

    def __init__(self, db_path: str = None, table_name: str = "memories",
                 embedding_model: str = None):
        self.db_path = db_path or self._default_db_path()
        self.table_name = table_name
        # Configurable embedding model (defaults to all-MiniLM-L6-v2)
        self.embedding_model_name = embedding_model or self._load_embedding_model_config()
        self.embedder = None
        self._db = None
        self._table = None
        self._local_embedder = None

        # Initialize
        self._init_lancedb()
        self._init_embedder()

    def _load_embedding_model_config(self) -> str:
        """Load embedding model name from config.json if available."""
        config_path = Path(__file__).parent.parent / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                model = config.get("memory", {}).get("embedding_model")
                if model:
                    return model
            except (json.JSONDecodeError, OSError):
                pass
        return "all-MiniLM-L6-v2"

    def _default_db_path(self) -> str:
        """Get default database path."""
        # Use centralized data/ directory
        base = Path(__file__).parent.parent
        return os.path.join(base, "data", "lancedb")

    def _init_lancedb(self):
        """Initialize LanceDB connection and table."""
        if not LANCEDB_AVAILABLE:
            print("[LanceDB] LanceDB not installed. Run: pip install lancedb")
            return

        try:
            # Create database directory
            os.makedirs(self.db_path, exist_ok=True)

            # Open LanceDB database
            self._db = lancedb.connect(self.db_path)

            # Create or get table
            existing_tables = self._db.table_names()
            
            if self.table_name in existing_tables:
                self._table = self._db.open_table(self.table_name)
            else:
                # Create table with schema (without index first)
                self._table = self._db.create_table(
                    self.table_name,
                    schema=self.SCHEMA,
                    exist_ok=True
                )
                # Try to create vector index (may fail on some LanceDB versions)
                try:
                    self._table.create_index(
                        vector_column_name="vector",
                        num_sub_vectors=96,
                        metric="cosine"
                    )
                except Exception as e:
                    logger.warning(f"Vector index creation skipped: {e}")

            print(f"[LanceDB] Connected to {self.db_path}")
            print(f"[LanceDB] Table: {self.table_name}, Rows: {len(self._table)}")

        except Exception as e:
            print(f"[LanceDB] Failed to initialize: {e}")
            self._db = None
            self._table = None

    def _init_embedder(self):
        """Initialize embedding function for vectorization."""
        if not ST_AVAILABLE:
            logger.warning("sentence-transformers not available. Using raw text matching.")
            return

        try:
            # Use the configured embedder (from config.json or default)
            self._local_embedder = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Embedder loaded: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedder '{self.embedding_model_name}': {e}")

    def _generate_id(self, content: str) -> str:
        """Generate unique memory ID."""
        unique = f"{content}{datetime.now().isoformat()}"
        return hashlib.sha256(unique.encode()).hexdigest()[:16]

    def _embed_text(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings for text."""
        if isinstance(texts, str):
            texts = [texts]

        if self._local_embedder is not None:
            embeddings = self._local_embedder.encode(texts)
            return embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings
        else:
            # Fallback: random vectors (NOT for production!)
            dim = 384  # MiniLM output dimension
            return np.random.rand(len(texts), dim).tolist()

    def add_memory(
        self,
        content: str,
        session_id: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_embed: bool = True
    ) -> str:
        """
        Add a memory to the vector store.
        
        Args:
            content: Memory text content
            session_id: Associated session ID
            importance: 0.0-1.0 importance score
            tags: List of tag strings
            metadata: Additional metadata dict
            auto_embed: Whether to auto-generate embedding
            
        Returns:
            Memory ID string
        """
        if self._table is None:
            print("[LanceDB] Table not available. Memory not saved.")
            return None

        memory_id = self._generate_id(content)
        timestamp = datetime.now().isoformat()

        # Generate embedding
        vector = None
        if auto_embed and self._local_embedder:
            vector = self._embed_text(content)[0]

        # Serialize metadata
        metadata_str = json.dumps(metadata or {})

        # Create record
        record = {
            "id": memory_id,
            "content": content,
            "session_id": session_id,
            "timestamp": timestamp,
            "importance": float(importance),
            "tags": tags or [],
            "metadata": metadata_str,
            "vector": vector
        }

        try:
            self._table.add([record])
            return memory_id
        except Exception as e:
            print(f"[LanceDB] Failed to add memory: {e}")
            return None

    def add_memories_batch(self, memories: List[Dict]) -> List[str]:
        """
        Add multiple memories at once (optimized for bulk insert).
        
        Args:
            memories: List of memory dicts with keys:
                - content (required)
                - session_id (optional)
                - importance (optional, default 0.5)
                - tags (optional)
                - metadata (optional)
                
        Returns:
            List of memory IDs
        """
        if self._table is None:
            return []

        if not memories:
            return []

        # Batch embed if possible
        texts = [m.get("content", "") for m in memories]
        vectors = None
        if self._local_embedder:
            vectors = self._embed_text(texts)

        records = []
        for i, mem in enumerate(memories):
            memory_id = self._generate_id(mem.get("content", "") + str(i))
            timestamp = datetime.now().isoformat()

            record = {
                "id": memory_id,
                "content": mem.get("content", ""),
                "session_id": mem.get("session_id"),
                "timestamp": timestamp,
                "importance": float(mem.get("importance", 0.5)),
                "tags": mem.get("tags", []),
                "metadata": json.dumps(mem.get("metadata", {})),
                "vector": vectors[i] if vectors else None
            }
            records.append(record)

        try:
            self._table.add(records)
            return [r["id"] for r in records]
        except Exception as e:
            print(f"[LanceDB] Batch add failed: {e}")
            return []

    def search(
        self,
        query: str,
        n_results: int = 5,
        session_id: Optional[str] = None,
        min_importance: float = 0.0,
        tags: Optional[List[str]] = None,
        filter_fn: Optional[callable] = None
    ) -> List[Dict]:
        """
        Semantic vector search for memories.
        
        Args:
            query: Search query text
            n_results: Max number of results
            session_id: Filter by session
            min_importance: Filter by minimum importance
            tags: Filter by tags (any match)
            filter_fn: Custom filter function (takes row dict, returns bool)
            
        Returns:
            List of matching memory dicts with scores
        """
        if self._table is None:
            return []

        try:
            # Generate query embedding
            query_embedding = self._embed_text(query)[0]

            # Build WHERE clause
            where_clauses = []
            if session_id:
                where_clauses.append(f'session_id = "{session_id}"')
            if min_importance > 0:
                where_clauses.append(f'importance >= {min_importance}')
            where = " AND ".join(where_clauses) if where_clauses else None

            # Vector search
            search_results = self._table.search(
                query=query_embedding,
                vector_column_name="vector"
            ).where(where) if where else self._table.search(
                query=query_embedding,
                vector_column_name="vector"
            )

            results = search_results.limit(n_results * 2).to_list()

            # Post-filter by tags and custom filter
            filtered = []
            for r in results:
                # Tag filter
                if tags:
                    mem_tags = r.get("tags", [])
                    if not any(t in mem_tags for t in tags):
                        continue

                # Custom filter
                if filter_fn and not filter_fn(r):
                    continue

                # Parse metadata
                r["metadata"] = json.loads(r.get("metadata", "{}"))

                filtered.append(r)

                if len(filtered) >= n_results:
                    break

            return filtered

        except Exception as e:
            print(f"[LanceDB] Search failed: {e}")
            return []

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a specific memory by ID."""
        if self._table is None:
            return None

        try:
            results = self._table.search(
                query=memory_id,
                vector_column_name="vector"
            ).where(f'id = "{memory_id}"').limit(1).to_list()

            if results:
                r = results[0]
                r["metadata"] = json.loads(r.get("metadata", "{}"))
                return r
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse metadata for memory {memory_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get memory {memory_id}: {e}")
            return None

    def get_recent_memories(
        self,
        hours: int = 24,
        limit: int = 100,
        session_id: Optional[str] = None
    ) -> List[Dict]:
        """Get recent memories within time window."""
        if self._table is None:
            return []

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

            where = f'timestamp >= "{cutoff}"'
            if session_id:
                where += f' AND session_id = "{session_id}"'

            results = self._table.search(
                query=np.zeros(384).tolist(),  # Dummy vector
                vector_column_name="vector"
            ).where(where).limit(limit).to_list()

            for r in results:
                r["metadata"] = json.loads(r.get("metadata", "{}"))

            return results
        except Exception as e:
            print(f"[LanceDB] Get recent failed: {e}")
            return []

    def update_memory(self, memory_id: str, updates: Dict) -> bool:
        """Update a memory's fields."""
        if self._table is None:
            return False

        try:
            # Get current row
            current = self.get_memory(memory_id)
            if not current:
                return False

            # Merge updates
            for key, value in updates.items():
                if key == "metadata":
                    current["metadata"] = json.dumps(value)
                elif key == "tags" and isinstance(value, list):
                    current["tags"] = value
                elif key in ["importance"]:
                    current[key] = float(value)

            current["timestamp"] = datetime.now().isoformat()

            # Update in table
            self._table.update(where=f'id = "{memory_id}"', values=current)
            return True
        except Exception as e:
            print(f"[LanceDB] Update failed: {e}")
            return False

    def update_importance(self, memory_id: str, importance: float) -> bool:
        """Update memory importance score."""
        return self.update_memory(memory_id, {"importance": importance})

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if self._table is None:
            return False

        try:
            self._table.delete(f'id = "{memory_id}"')
            return True
        except Exception as e:
            print(f"[LanceDB] Delete failed: {e}")
            return False

    def delete_old_memories(self, days: int = 30, min_importance: float = 0.3) -> int:
        """Delete memories older than N days with low importance."""
        if self._table is None:
            return 0

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            where = f'timestamp < "{cutoff}" AND importance < {min_importance}'

            # Count before delete
            count = len(self._table.where(where).to_list())

            # Delete
            self._table.delete(where)
            return count
        except Exception as e:
            print(f"[LanceDB] Delete old failed: {e}")
            return 0

    # ===== User Profile Operations =====

    def set_user_profile(self, key: str, value: str, confidence: float = 0.5) -> bool:
        """Set a user profile attribute."""
        profile_table = self._get_or_create_table("user_profiles", USER_PROFILE_SCHEMA)
        if profile_table is None:
            return False

        try:
            # Upsert
            existing = profile_table.search(query=key, vector_column_name="key_vector").limit(1).to_list()
            
            if existing:
                profile_table.update(
                    where=f'profile_key = "{key}"',
                    values={
                        "profile_value": value,
                        "confidence": float(confidence),
                        "updated_at": datetime.now().isoformat()
                    }
                )
            else:
                profile_table.add([{
                    "profile_key": key,
                    "profile_value": value,
                    "confidence": float(confidence),
                    "updated_at": datetime.now().isoformat(),
                    "key_vector": self._embed_text(key)[0] if self._local_embedder else None
                }])
            return True
        except Exception as e:
            print(f"[LanceDB] Set profile failed: {e}")
            return False

    def get_user_profile(self, key: str) -> Optional[Dict]:
        """Get a user profile attribute."""
        profile_table = self._get_or_create_table("user_profiles", USER_PROFILE_SCHEMA)
        if profile_table is None:
            return None

        try:
            results = profile_table.search(query=key, vector_column_name="key_vector").limit(1).to_list()
            if results:
                return {
                    "key": results[0]["profile_key"],
                    "value": results[0]["profile_value"],
                    "confidence": results[0]["confidence"],
                    "updated_at": results[0]["updated_at"]
                }
            return None
        except Exception as e:
            logger.debug(f"Failed to get user profile '{key}': {e}")
            return None

    def get_all_user_profiles(self) -> Dict[str, Dict]:
        """Get all user profile attributes."""
        profile_table = self._get_or_create_table("user_profiles", USER_PROFILE_SCHEMA)
        if profile_table is None:
            return {}

        try:
            results = profile_table.to_list()
            profiles = {}
            for r in results:
                profiles[r["profile_key"]] = {
                    "value": r["profile_value"],
                    "confidence": r["confidence"],
                    "updated_at": r["updated_at"]
                }
            return profiles
        except Exception as e:
            logger.debug(f"Failed to get all user profiles: {e}")
            return {}

    def _get_or_create_table(self, name: str, schema) -> Optional[Table]:
        """Get or create a named table."""
        if self._db is None:
            return None

        try:
            existing = self._db.table_names()
            if name in existing:
                return self._db.open_table(name)
            else:
                table = self._db.create_table(name, schema=schema, exist_ok=True)
                return table
        except Exception as e:
            print(f"[LanceDB] Table {name} failed: {e}")
            return None

    # ===== Utility Methods =====

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            "lancedb_available": LANCEDB_AVAILABLE,
            "embedder_available": self._local_embedder is not None,
            "db_path": self.db_path,
            "tables": []
        }

        if self._db:
            try:
                stats["tables"] = self._db.table_names()
                for table_name in stats["tables"]:
                    try:
                        table = self._db.open_table(table_name)
                        stats[f"table_{table_name}_rows"] = len(table)
                    except Exception as e:
                        logger.debug(f"Could not read table stats for '{table_name}': {e}")
            except Exception as e:
                logger.debug(f"Could not list tables: {e}")

        return stats

    def optimize(self):
        """Optimize table indices and compaction."""
        if self._table is None:
            return

        try:
            # Trigger compaction
            self._table.compact_files()
            print("[LanceDB] Table optimized")
        except Exception as e:
            print(f"[LanceDB] Optimize failed: {e}")

    def backup(self, backup_path: str = None) -> str:
        """Create a backup of the database."""
        if self._db is None:
            return None

        if backup_path is None:
            backup_path = os.path.join(self.db_path, "..", "backups", datetime.now().strftime("%Y%m%d_%H%M%S"))

        try:
            os.makedirs(backup_path, exist_ok=True)
            
            # Copy entire db directory
            import shutil
            shutil.copytree(self.db_path, os.path.join(backup_path, "lancedb"), dirs_exist_ok=True)
            
            print(f"[LanceDB] Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"[LanceDB] Backup failed: {e}")
            return None

    def close(self):
        """Close database connections."""
        # LanceDB doesn't require explicit close
        self._db = None
        self._table = None

    def __len__(self) -> int:
        """Get total memory count."""
        if self._table is None:
            return 0
        return len(self._table)


# User Profile Schema
USER_PROFILE_SCHEMA = pa.schema([
    pa.field("profile_key", pa.string()),
    pa.field("profile_value", pa.string()),
    pa.field("confidence", pa.float32()),
    pa.field("updated_at", pa.string()),
    pa.field("key_vector", pa.list_(pa.float32()), nullable=True),
])


# Singleton instance
_db_instance = None

def get_vector_db() -> LanceDBVectorStore:
    """Get or create singleton VectorDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = LanceDBVectorStore()
    return _db_instance


# Backwards compatibility alias for tests and legacy imports
VectorDB = LanceDBVectorStore
