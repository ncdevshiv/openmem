# LanceMem Documentation

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Architecture](#architecture)
5. [CLI Reference](#cli-reference)
6. [API Reference](#api-reference)
7. [OpenClaw Integration](#openclaw-integration)
8. [Other Agent Integration](#other-agent-integration)
9. [Prompt Integration](#prompt-integration)
10. [Configuration](#configuration)
11. [Troubleshooting](#troubleshooting)

---

## Overview

**LanceMem** is an autonomous memory system for AI agents, powered by LanceDB.

### What It Does

- 🧠 **Autonomous Learning** — Self-run learning cycles without human intervention
- 🔍 **Semantic Memory** — Vector-based search over all conversation history
- 📦 **Skill Auto-Generation** — Creates skills from recurring patterns
- 🔄 **Self-Optimization** — Matrix-based pruning using LanceDB
- 🧬 **Self-Evolution** — Genetic algorithms evolve skills autonomously
- 👤 **Auto User Modeling** — Learns user preferences automatically

### Why LanceDB?

| Feature | Benefit |
|---------|---------|
| Sub-millisecond search | Fast memory retrieval |
| Billions of vectors | Infinite scaling |
| Table versioning | Memory version history |
| Schema evolution | Add memory types anytime |
| Cloud native | S3/GCS backup |
| ACID transactions | Reliable writes |

---

## Quick Start

### 5-Minute Setup

```bash
# 1. Clone or download
cd F:\openmem

# 2. Install dependencies
pip install lancedb sentence-transformers

# 3. Initialize
python main.py init

# 4. Run first cycle
python main.py run-cycle

# 5. Start autonomous daemon
python main.py daemon start --interval 2
```

### Verify Installation

```bash
python main.py status
```

---

## Installation

### Option 1: pip (Recommended)

```bash
pip install lancedb>=0.12.0
pip install sentence-transformers>=2.2.0
```

### Option 2: Binary Manager (For Server Deployment)

```bash
python bin/lancedb_manager.py install
python bin/lancedb_manager.py start --port 8080
```

### Option 3: Docker

```bash
docker run -p 8080:8080 \
  -v /path/to/data:/data \
  lancedb/lancedb-server
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LanceMem System                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐ │
│  │   OpenClaw   │     │    Other     │     │   Direct   │ │
│  │    Agent     │     │    Agents    │     │    CLI     │ │
│  └──────┬───────┘     └──────┬───────┘     └─────┬──────┘ │
│         │                     │                    │         │
│         └─────────────────────┼────────────────────┘         │
│                               │                              │
│                    ┌──────────▼──────────┐                   │
│                    │   /learn Commands   │                   │
│                    │   (OpenClaw Skill)   │                   │
│                    └──────────┬──────────┘                   │
│                               │                              │
│         ┌─────────────────────┼─────────────────────┐       │
│         │                     │                     │       │
│  ┌──────▼──────┐    ┌────────▼────────┐   ┌──────▼──────┐ │
│  │  Learning    │    │     Skill       │   │   Memory    │ │
│  │    Loop     │    │   Generator     │   │   Store     │ │
│  └──────┬──────┘    └────────┬────────┘   └──────┬──────┘ │
│         │                     │                     │       │
│  ┌──────▼──────┐    ┌────────▼────────┐   ┌──────▼──────┐ │
│  │ Conversation │    │    Pattern      │   │   LanceDB   │ │
│  │  Indexer    │    │  Recognizer    │   │  Vector DB  │ │
│  └──────┬──────┘    └────────┬────────┘   └──────┬──────┘ │
│         │                     │                     │       │
│         └─────────────────────┼─────────────────────┘       │
│                               │                              │
│                    ┌──────────▼──────────┐                   │
│                    │   Self-Optimizer    │                   │
│                    │   (Matrix Pruning)  │                   │
│                    └──────────┬──────────┘                   │
│                               │                              │
│                    ┌──────────▼──────────┐                   │
│                    │   Self-Evolution    │                   │
│                    │ (Genetic Algorithm) │                   │
│                    └─────────────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Message
     │
     ▼
┌─────────────┐
│  Indexer    │ ──► LanceDB (memories)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Pattern    │ ──► Skill Generator
│ Recognizer  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Reflection │ ──► Self-Optimizer
│   Engine    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Evolution  │ ──► Evolved Skills
│   Engine    │
└──────┬──────┘
       │
       ▼
   Agent Response
   (with memory context)
```

---

## CLI Reference

### Core Commands

```bash
# Initialize system
python main.py init

# Run learning cycle
python main.py run-cycle
python main.py run-cycle --full  # Full re-index

# Daemon mode (autonomous)
python main.py daemon start --interval 2  # Every 2 hours
python main.py daemon stop
python main.py daemon status

# Search
python main.py search "query text"
python main.py search "query" --limit 20

# Status & Stats
python main.py status
python main.py stats
python main.py profile
```

### Learning Commands

```bash
# Via /learn skill
python main.py learn run
python main.py learn status
python main.py learn patterns
python main.py learn skills
python main.py learn search <query>
python main.py learn stats
python main.py learn profile
python main.py learn optimize
python main.py learn evolve
```

### LanceDB Binary Manager

```bash
# Install LanceDB binary
python bin/lancedb_manager.py install
python bin/lancedb_manager.py install --force

# Server management
python bin/lancedb_manager.py start --port 8080
python bin/lancedb_manager.py stop
python bin/lancedb_manager.py status

# Database
python bin/lancedb_manager.py init --path /data/mydb
```

---

## API Reference

### Python API

```python
from lance_mem import LanceMem

# Initialize
mem = LanceMem()

# Add conversation
mem.add_message("user", "Build me a Python API")
mem.add_message("agent", "Here's a Flask API...")

# Search memories
results = mem.search("Python API")
for r in results:
    print(r['content'], r.get('_distance'))

# Get user profile
profile = mem.get_user_profile()

# Run learning cycle
report = mem.run_cycle()

# Run optimization
optimization_report = mem.optimize()

# Run evolution
evolution_report = mem.evolve()
```

### Direct Module Import

```python
# Vector DB
from memory_store.vector_db import get_vector_db, LanceDBVectorStore

db = get_vector_db()
db.add_memory(content="Important info", importance=0.8)
results = db.search("info", n_results=5)

# Memory Manager
from memory_store.memory_manager import MemoryManager

mm = MemoryManager()
mm.store_daily_memory("2026-04-02", "Event happened")
context = mm.get_memory_context("query")

# User Model
from memory_store.user_model import UserModel

model = UserModel()
model.analyze_message("Hello, my name is Shivam")
summary = model.get_profile_summary()

# Self-Optimizer
from autonomous import get_optimizer

optimizer = get_optimizer()
optimizer.register_entity("skill_python", "skill")
optimizer.record_usage("skill_python", success=True)
report = optimizer.run_optimization_cycle()

# Evolution Engine
from autonomous import EvolutionEngine

evo = EvolutionEngine()
evo.create_initial_population()
report = evo.evolve()
```

---

## OpenClaw Integration

### Method 1: Skill Installation

```bash
# Copy skill to OpenClaw skills directory
cp -r skills/self_learning ~/.openclaw/skills/

# Restart OpenClaw
openclaw gateway restart
```

### Method 2: Via Command

```
/learn install
/learn init
/learn run
```

### Available /learn Commands

| Command | Description |
|---------|-------------|
| `/learn run` | Run full learning cycle |
| `/learn status` | System status |
| `/learn install` | Install LanceDB |
| `/learn init` | Initialize database |
| `/learn search <q>` | Search memories |
| `/learn patterns` | Show patterns |
| `/learn skills` | List skills |
| `/learn stats` | Statistics |
| `/learn profile` | User profile |
| `/learn optimize` | Run optimization |
| `/learn evolve` | Run evolution |

---

## Other Agent Integration

### LangChain

```python
from langchain.agents import Agent
from lance_mem import LanceMem

# Initialize LanceMem
mem = LanceMem()

# Add to LangChain agent
class LanceMemTool:
    name = "lance_memory"
    description = "Search long-term memory"
    
    def _run(self, query):
        results = mem.search(query)
        return "\n".join([r['content'] for r in results])

# Add tool to agent
tools = [LanceMemTool(), ...]
agent = Agent(..., tools=tools)
```

### AutoGPT /自主Agent

```python
from lance_mem import LanceMem

class AutonomousAgent:
    def __init__(self):
        self.memory = LanceMem()
    
    def think(self, task):
        # Search relevant memories
        context = self.memory.search(task)
        
        # Learn from action
        result = self.execute(task, context)
        
        # Store result
        self.memory.add_message("agent", str(result))
        
        return result
```

### CrewAI

```python
from crewai import Agent, Task
from lance_mem import LanceMem

mem = LanceMem()

researcher = Agent(
    role="Researcher",
    memory=mem  # LanceMem as memory backend
)

task = Task(
    description="Research AI trends",
    agent=researcher
)
```

---

## Prompt Integration

### Single-Prompt Agent Integration

See `doc/PROMPT_INTEGRATION.md` for the complete prompt to add autonomous memory to any agent.

### Basic Integration Prompt

```markdown
You have access to LanceMem, an autonomous memory system.

Setup:
1. pip install lancedb sentence-transformers
2. python main.py init

Commands:
- /learn run - Run learning cycle
- /learn search <query> - Search memories
- /learn status - System status

To use in your agent loop:
1. After each user message: mem.add_message("user", message)
2. After each response: mem.add_message("agent", response)
3. Before responding: context = mem.search(user_message)
```

### Advanced Integration

See `doc/PROMPT_INTEGRATION.md` for the complete 500+ line integration prompt.

---

## Configuration

### Environment Variables

```bash
# LanceMem paths
LANCE_MEM_ROOT=/path/to/lancemem
LANCE_DB_PATH=/path/to/lancedb/data

# Server settings
LANCE_HOST=localhost
LANCE_PORT=8080

# Learning settings
LEARNING_INTERVAL_HOURS=2
PRUNE_THRESHOLD=0.2
EVOLUTION_POPULATION=20
```

### Config File

Create `config.json`:

```json
{
  "lance_db": {
    "path": "./data/lancedb",
    "host": "localhost",
    "port": 8080
  },
  "learning": {
    "interval_hours": 2,
    "index_hours_back": 24,
    "pattern_days_back": 7,
    "min_pattern_frequency": 3
  },
  "optimization": {
    "prune_threshold": 0.2,
    "strengthen_threshold": 0.7,
    "prune_age_days": 30
  },
  "evolution": {
    "population_size": 20,
    "mutation_rate": 0.15,
    "crossover_rate": 0.3,
    "elite_ratio": 0.2
  }
}
```

---

## Troubleshooting

### LanceDB Won't Start

```bash
# Check installation
python bin/lancedb_manager.py status

# Reinstall
python bin/lancedb_manager.py install --force

# Or use pip
pip install lancedb --upgrade
```

### Import Errors

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify
python -c "import lancedb; print('OK')"
```

### Vector Search Not Working

```bash
# Install embedder
pip install sentence-transformers

# Verify
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

### OpenClaw Skill Not Found

```bash
# Copy skill
cp -r skills/self_learning ~/.openclaw/skills/

# Verify
ls ~/.openclaw/skills/self_learning/
```

### Out of Memory

```bash
# Reduce batch size in vector_db.py
BATCH_SIZE = 100  # Default 1000

# Or disable auto-embedding
auto_embed=False
```

---

## License

Apache 2.0

---

## Support

- GitHub Issues: [link]
- Discord: [link]
- Docs: [link]
