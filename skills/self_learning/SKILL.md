# LanceMem Self-Learning

_Autonomous memory system powered by LanceDB for AI agents._

## Overview

LanceMem brings **Hermes-style autonomous learning** to any AI agent using LanceDB as the backbone.

- 🧠 **Autonomous Learning** — Self-run learning cycles every 2 hours
- 🔍 **Semantic Memory** — LanceDB-powered vector search over all conversations
- 📦 **Skill Auto-Generation** — Creates skills from recurring patterns
- 🔄 **Self-Optimization** — Matrix-based pruning with LanceDB
- 🧬 **Self-Evolution** — Genetic algorithms evolve skills autonomously
- 👤 **Auto User Modeling** — Learns user preferences automatically

## Setup

### 1. Install LanceDB

```bash
# Option A: Via skill command
/learn install

# Option B: Via pip
pip install lancedb sentence-transformers

# Option C: Via binary manager
python bin/lancedb_manager.py install
```

### 2. Initialize Database

```bash
/learn init
# or
python main.py init
```

### 3. Start Autonomous Daemon

```bash
python main.py daemon start --interval 2
```

## Commands

| Command | Description |
|---------|-------------|
| `/learn run` | Run full learning cycle |
| `/learn status` | Show system status |
| `/learn install` | Install LanceDB binary |
| `/learn init` | Initialize database |
| `/learn search <query>` | Semantic memory search |
| `/learn patterns` | Show discovered patterns |
| `/learn skills` | List auto-generated skills |
| `/learn stats` | Show statistics |
| `/learn profile` | Show user profile |
| `/learn optimize` | Run optimization cycle |
| `/learn evolve` | Run evolution cycle |

## Architecture

```
LanceMem/
├── memory_store/        # LanceDB-powered storage
│   ├── vector_db.py    # LanceDB + embeddings
│   ├── memory_manager.py
│   ├── user_model.py
│   └── skill_generator.py
├── learning_loop/       # Autonomous learning
│   ├── conversation_indexer.py
│   ├── pattern_recognizer.py
│   ├── reflection_engine.py
│   └── scheduler.py
├── autonomous/          # Self-optimization
│   ├── self_optimizer.py   # LanceDB matrix pruner
│   └── self_evolution.py   # Genetic algorithms
├── bin/
│   └── lancedb_manager.py # LanceDB binary manager
└── skills/
    └── self_learning/  # OpenClaw skill
```

## LanceDB Benefits

| Feature | Benefit |
|---------|---------|
| **Sub-millisecond search** | Fast memory retrieval |
| **Automatic indexing** | Zero-config optimization |
| **Table versioning** | Memory version history |
| **Schema evolution** | Add memory types anytime |
| **Cloud backup** | S3/GCS integration |
| **ACID transactions** | Reliable memory writes |

## Comparison

| | Hermes Agent | LanceMem |
|-|-------------|----------|
| Memory DB | Native | LanceDB |
| Self-learning | ✅ | ✅ |
| Auto skills | ✅ | ✅ |
| Self-optimize | ✅ | ✅ |
| Self-evolve | ✅ | ✅ |
| Open source | ✅ MIT | ✅ Apache 2.0 |

## Installation for Any Agent

```python
# Add to your agent:
from lance_mem import LanceMem

mem = LanceMem()
mem.install()  # Install LanceDB
mem.init()     # Initialize DB

# Use in conversation
mem.add_message(user="Build me a Python API")
mem.add_message(agent="Here's the API...")

# Search memories
results = mem.search("Python API")

# Run learning cycle
mem.run_cycle()
```

## Files

- `learner.py` — Skill execution logic
- OpenClaw calls via `/learn` prefix
- Fully autonomous — no human intervention needed
