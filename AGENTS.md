# AGENTS.md - OpenMem Development Guide

Self-learning memory system for AI agents with vector-based semantic search, automatic user profiling, pattern recognition, and skill auto-generation.

## Project Structure

```
F:\openmem\
├── memory_store/           # Core memory systems
│   ├── vector_db.py        # LanceDB vector store
│   ├── memory_manager.py   # Memory tier management
│   ├── user_model.py       # User profiling
│   └── skill_generator.py  # Skill auto-generation
├── learning_loop/          # Autonomous learning engine
│   ├── conversation_indexer.py
│   ├── pattern_recognizer.py
│   ├── reflection_engine.py
│   └── scheduler.py
├── autonomous/             # Self-evolution
│   ├── self_optimizer.py
│   └── self_evolution.py
├── skills/                 # OpenClaw integration
├── bin/                    # Utilities
└── tests/                  # unittest suite
```

## Build/Lint/Test Commands

```bash
# Run quick test suite
python test_runner.py

# Run all tests in a specific file
python -m unittest tests/test_memory_store.py

# Run a specific test class
python -m unittest tests.test_memory_store.TestVectorDB

# Run a single test
python -m unittest tests.test_memory_store.TestVectorDB.test_add_memory

# Run all tests
python -m unittest discover -s tests

# Application commands
python main.py status        # Check system status
python main.py install       # Install LanceDB binary
python main.py init          # Initialize database
python main.py run-cycle     # Run full learning cycle
python main.py run-cycle --full  # Full re-index
python main.py search "query" --limit 10  # Search memories
python main.py profile       # Show user profile
python main.py stats         # Show statistics
python main.py daemon start --interval 2   # Run as daemon

# Install dependencies
pip install -r requirements.txt
```

## Code Style Guidelines

### General
- Python 3.x, type hints from `typing` module (`List`, `Dict`, `Optional`, `Any`)
- f-strings for formatting, 4 spaces indentation, lines under 120 chars

### Imports
Standard library → third-party → local. Use `sys.path.insert(0, str(BASE_DIR))` at module top. Group by type:

```python
import os, sys, json
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import lancedb
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False

from memory_store import get_vector_db
```

### Naming
- Classes: `PascalCase` (e.g., `MemoryManager`)
- Functions/Variables: `snake_case` (e.g., `get_memory_context`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `USER_PROFILE_SCHEMA`)
- Private methods: prefix `_` (e.g., `_init_db`)

### Data Classes
```python
from dataclasses import dataclass

@dataclass
class Memory:
    id: str
    content: str
    session_id: Optional[str]
    timestamp: str
    importance: float
    tags: List[str]
    metadata: Dict[str, Any]
    vector: Optional[List[float]] = None
```

### Docstrings
Google-style for public functions/classes:
```python
def search_memory(self, query: str, n_results: int = 5) -> List[Dict]:
    """
    Search across all memory tiers.

    Args:
        query: Search query text
        n_results: Maximum number of results

    Returns:
        List of matching memory dicts with scores
    """
```

### Error Handling
- Specific exception types when possible
- Return `None`/empty collections for "not found" cases
- Try/except for optional dependencies:
```python
try:
    import lancedb
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("[LanceDB] Not installed. Run: pip install lancedb")
```

### Database Patterns (Singleton)
```python
_db_instance = None

def get_vector_db() -> LanceDBVectorStore:
    global _db_instance
    if _db_instance is None:
        _db_instance = LanceDBVectorStore()
    return _db_instance
```
- Close connections in `finally` or `close()` methods
- Use `tempfile.mkdtemp()` for test fixtures, clean in `tearDown`

### Testing Patterns
```python
class TestVectorDB(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db = VectorDB(db_path=os.path.join(self.test_dir, "test_vectordb"))

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)
```
- Descriptive names: `test_add_memory`, `test_search_session_filter`
- Use `assertIsNotNone`, `assertIsInstance`, `assertEqual`

### Logging
Print statements with prefixes: `[LanceDB]`, `[OpenMem]`. Errors: `traceback.print_exc()`.

### Path Handling
```python
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
```
Use `os.path.join()` for cross-platform paths.

### CLI Structure (main.py pattern)
```python
def cmd_run_cycle(args):
    scheduler = LearningScheduler()
    report = scheduler.run_cycle(full=args.full)
    return 0 if report.get('success') else 1
```
Use argparse with subparsers, return 0 for success, 1 for failure.

## Key Dependencies
- `lancedb>=0.12.0`: Vector database
- `sentence-transformers>=2.2.0`: Text embeddings
- `torch>=2.0.0`: ML backend
- `numpy>=1.24.0`, `pandas>=2.0.0`: Data processing

## Architecture

### Memory Tiers
1. **Daily** (importance 0.6): Raw events and logs
2. **Weekly** (0.7): Condensed from daily
3. **Long-term** (0.9): Important distilled facts

### Vector Store
- LanceDB-backed for sub-millisecond search
- Auto-embedding via `all-MiniLM-L6-v2`
- Schema evolution supported

### Pattern Recognition
- Request types: `factual_question`, `build_request`, `problem_solving`, etc.
- Response strategies: `concise_direct`, `structured_format`, `code_oriented`

## File Locations
- Database: `data/lancedb/`
- Memory metadata: `data/memory/memory_meta.db` (SQLite)
- Patterns: `data/patterns.json`
- Generated skills: `generated_skills/`
- OpenClaw workspace: `~/.openclaw/workspace`
