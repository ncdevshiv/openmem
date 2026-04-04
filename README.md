# OpenMem — Agent-Agnostic Autonomous Memory System

Universal memory layer for **any** AI coding agent. Works with Qwen Code, Claude Code, Cursor, VS Code, OpenClaw, Windsurf, Codex CLI, OpenCode, Antigravity IDE, Kilo CLI, and more.

## What It Does

- 🔍 **Semantic Memory Search** — Vector-based embedding search across all conversation history
- 🧠 **Auto User Profiling** — Learns your preferences, habits, and communication style
- 📦 **Skill Auto-Generation** — Creates skills from recurring successful patterns
- 🔄 **Self-Correction Loop** — Reflection engine that evaluates and improves after each session
- 📅 **Memory Consolidation** — Daily → Weekly → Long-term memory distillation
- ⚡ **Proactive Learning** — Scheduled cycles that run autonomously
- 🧬 **Self-Evolution** — Genetic algorithm optimization of response strategies

## Supported Agents

| Agent | Trigger | Context File | Adapter |
|---|---|---|---|
| **Qwen Code** | `/mem` | `.qwen/memory_context.md` | ✅ `agents/qwen_code/` |
| **Claude Code** | `/mem` | `CLAUDE.md` | ✅ `agents/claude_code/` |
| **Codex CLI** | `/mem` | `.codex/context.md` | ✅ `agents/codex_cli/` |
| **OpenCode** | `/memory` | `.opencode/context.md` | ✅ `agents/opencode/` |
| **Antigravity IDE** | `/mem` | `.antigravity/memory.md` | ✅ `agents/antigravity_ide/` |
| **Kilo CLI** | `/mem` | `.kilo/context.md` | ✅ `agents/kilo_cli/` |
| **VS Code** | `/mem` | `.vscode/memory.md` | ✅ `agents/vscode/` |
| **Windsurf** | `@memory` | `.windsurf/memory.md` | ✅ `agents/windsurf/` |
| **Cursor** | `@memory` | `.cursor/rules/memory.md` | ✅ `agents/cursor/` |
| **OpenClaw** | `/lm` | `~/.openclaw/memory_context.md` | ✅ `agents/openclaw/` |
| **Any Agent** | — | file-based sessions | ✅ `agents/generic/` |

## Quick Start

```bash
cd F:\openmem

# One-command install & setup
python bin/install.py

# Check status
python main.py status

# Run first learning cycle
python main.py run-cycle

# Search memories
python main.py search "what is my project"
```

## Universal Launcher

The `bin/launcher.py` auto-detects which agent you're using and adapts automatically:

```bash
# Auto-detect agent, show status
python bin/launcher.py

# Force specific agent
python bin/launcher.py --agent qwen_code
python bin/launcher.py --agent cursor
python bin/launcher.py --agent claude_code

# Install skills for an agent
python bin/launcher.py --skill cursor
python bin/launcher.py --skill all

# Run learning cycle
python bin/launcher.py --run-cycle

# Search memories
python bin/launcher.py --search python programming

# Start autonomous daemon
python bin/launcher.py --daemon --interval 2
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your Agent                                   │
│  Qwen Code │ Claude Code │ Cursor │ VS Code │ Windsurf │ OpenClaw │ ... │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
            ┌──────────────▼──────────────┐
            │     AgentAdapter Interface   │
            │  agents/base.py (contract)   │
            └──┬──┬──┬──┬──┬──┬──┬──┬──┬─┘
               │  │  │  │  │  │  │  │  │
  ┌────────────┤  │  │  │  │  │  │  │  ├────────────┐
  │            │  │  │  │  │  │  │  │  │            │
  ▼            ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼            ▼
agents/    agents/ ...                              agents/
qwen_code/  claude_code/                            generic/
  skill/      skill/                                  skill/
  adapter.py  adapter.py                              adapter.py
  config.json config.json                             config.json
                           │
            ┌──────────────▼──────────────┐
            │      OpenMem Core           │
            │  memory_store/               │
            │  learning_loop/              │
            │  autonomous/                 │
            └──────────────┬──────────────┘
                           │
            ┌──────────────▼──────────────┐
            │   bin/ (Fully Portable)      │
            │  launcher.py                 │
            │  install.py                  │
            │  config_generator.py         │
            │  manifest.json               │
            └─────────────────────────────┘
```

## Directory Structure

```
F:\openmem\
├── main.py                         # Unified entry point
├── config.json                     # Auto-generated configuration
├── requirements.txt                # Dependencies
│
├── bin/                            # ★ FULLY PORTABLE
│   ├── launcher.py                 # Universal launcher (auto-detects agent)
│   ├── install.py                  # One-command installer
│   ├── config_generator.py         # Generates per-agent config
│   ├── generate_skills.py          # Generates skill files
│   ├── manifest.json               # System manifest
│   ├── portable_env.bat / .sh      # Environment setup scripts
│   └── run.bat / run.sh            # Entry point scripts
│
├── agents/                         # ★ AGENT-AGNOSTIC LAYER
│   ├── base.py                     # AbstractAdapter interface contract
│   ├── qwen_code/                  # Qwen Code adapter + skill
│   ├── claude_code/                # Claude Code adapter + skill
│   ├── codex_cli/                  # Codex CLI adapter + skill
│   ├── opencode/                   # OpenCode adapter + skill
│   ├── antigravity_ide/            # Antigravity IDE adapter + skill
│   ├── kilo_cli/                   # Kilo CLI adapter + skill
│   ├── vscode/                     # VS Code adapter + skill
│   ├── windsurf/                   # Windsurf adapter + skill
│   ├── cursor/                     # Cursor adapter + skill
│   ├── openclaw/                   # OpenClaw adapter + skill
│   └── generic/                    # Fallback for any agent
│       └── (each has adapter.py, skill/, config.json)
│
├── memory_store/                   # Core memory systems
│   ├── vector_db.py                # LanceDB vector store
│   ├── memory_manager.py           # Tier management (daily/weekly/longterm)
│   ├── user_model.py               # Automatic user profiling
│   └── skill_generator.py          # Pattern → Skill conversion
│
├── learning_loop/                  # Autonomous learning engine
│   ├── scheduler.py                # Orchestrates learning cycles
│   ├── conversation_indexer.py     # Indexes session transcripts
│   ├── pattern_recognizer.py       # Statistical pattern detection
│   └── reflection_engine.py        # Self-correction & improvement
│
├── autonomous/                     # Self-evolution
│   ├── self_optimizer.py           # Performance matrix optimization
│   └── self_evolution.py           # Genetic algorithm evolution
│
├── tests/                          # Test suite
│   ├── test_memory_store.py
│   ├── test_learning_loop.py
│   └── test_integration.py
│
└── data/                           # Runtime data (auto-created, gitignored)
    ├── lancedb/                    # Vector database
    ├── memory/                     # Tiered memory (daily/weekly/longterm)
    ├── optimizer/                  # Performance optimization data
    ├── evolution/                  # Evolution state
    ├── sessions/                   # Session index state
    └── usermodel/                  # User profile data
```

## How Each Agent Integrates

Every agent adapter follows the same contract:

1. **Read sessions** — Parse the agent's session/conversation files
2. **Inject context** — Write memory context to the agent's preferred context file
3. **Install skills** — Copy SKILL.md + learner.py to the agent's skill directory
4. **Hook messages** — Optional callback for real-time message indexing

### Example: Qwen Code

```bash
# Auto-detected when running from a workspace with .qwen/
python main.py --agent qwen_code

# Installs skill to workspace skills/memory/
python main.py --skill qwen_code

# Memory context written to .qwen/memory_context.md
# Sessions read from ~/.qwen/sessions/
```

### Example: Cursor

```bash
# Memory context written to .cursor/rules/memory.md (Cursor auto-reads rules/)
python main.py --skill cursor

# Sessions read from .cursor/ or ~/.cursor/sessions/
```

### Example: Claude Code

```bash
# Memory context injected into CLAUDE.md in workspace root
python main.py --skill claude_code
```

### Generic (Any Agent)

```bash
# Works with any agent that stores sessions as JSON files
# Set GENERIC_SESSION_DIR or use workspace .sessions/ directory
export OPENMEM_AGENT=generic
python main.py run-cycle
```

## Configuration

Auto-generated by `bin/config_generator.py`:

```json
{
  "agent": "auto-detect",
  "memory": {
    "db_path": "data/lancedb",
    "embedding_model": "all-MiniLM-L6-v2"
  },
  "learning": {
    "auto_learn": true,
    "interval_hours": 2
  },
  "agents": {
    "qwen_code": { "enabled": true },
    "claude_code": { "enabled": true },
    "cursor": { "enabled": true }
  }
}
```

## Portability

Everything is self-contained in this directory:

- ✅ **Windows, Linux, macOS**
- ✅ **Zero-config defaults** — auto-detects agent, creates data dirs
- ✅ **Portable env scripts** — `source bin/portable_env.sh` or `bin\portable_env.bat`
- ✅ **Single entry point** — `python main.py` or `python bin/launcher.py`
- ✅ **All paths relative** — no hardcoded absolute paths

## Commands

```bash
# Core
python main.py install            # Full installation
python main.py status             # System status
python main.py run-cycle          # Run learning cycle
python main.py run-cycle --full   # Full re-index

# Memory
python main.py search "query"     # Semantic search
python main.py profile            # User profile
python main.py stats              # Statistics

# Agent management
python main.py --agents           # List supported agents
python main.py --skill cursor     # Install Cursor skill
python main.py --skill all        # Install all skills

# Daemon
python main.py daemon             # Start daemon (via launcher)
```

## For Developers

### Adding a New Agent Adapter

1. Create `agents/my_agent/__init__.py` and `agents/my_agent/adapter.py`
2. Subclass `AgentAdapter` from `agents/base.py`
3. Implement the 6 required methods
4. Create `agents/my_agent/skill/` with `SKILL.md`, `learner.py`, `config.json`
5. Register: `register_adapter("my_agent", MyAgentAdapter)`

### Adding a New Skill

Skills live in `agents/<name>/skill/`. Edit `SKILL.md` and `learner.py` for agent-specific commands.

## License

MIT
