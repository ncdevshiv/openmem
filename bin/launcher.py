#!/usr/bin/env python3
"""
OpenMem Universal Launcher.

Auto-detects the calling agent, loads config, and provides unified CLI.
Fully portable — all paths are relative to this script's location.

Usage:
    python bin/launcher.py                    # Auto-detect, show status
    python bin/launcher.py --agent qwen       # Force Qwen Code mode
    python bin/launcher.py --install          # Run full installation
    python bin/launcher.py --status           # System status
    python bin/launcher.py --run-cycle        # Run learning cycle
    python bin/launcher.py --search "query"   # Search memories
    python bin/launcher.py --skill qwen       # Install skill for agent
    python bin/launcher.py --skill all        # Install all skills
    python bin/launcher.py --daemon           # Start daemon
    python bin/launcher.py --config           # Show current config
    python bin/launcher.py --agents           # List supported agents
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Portable path resolution
BIN_DIR = Path(__file__).parent
OPENMEM_ROOT = BIN_DIR.parent
DATA_DIR = OPENMEM_ROOT / "data"
CONFIG_FILE = OPENMEM_ROOT / "config.json"

# Ensure OpenMem is importable
sys.path.insert(0, str(OPENMEM_ROOT))

# Supported agents
SUPPORTED_AGENTS = [
    "qwen_code", "claude_code", "codex_cli", "opencode",
    "antigravity_ide", "kilo_cli", "vscode", "windsurf",
    "cursor", "openclaw", "generic"
]


def load_config():
    """Load configuration file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return get_default_config()


def get_default_config():
    """Return default configuration."""
    return {
        "version": "2.0.0",
        "agent": "auto-detect",
        "memory": {
            "db_path": str(DATA_DIR / "lancedb"),
            "embedding_model": "all-MiniLM-L6-v2",
        },
        "learning": {
            "auto_learn": True,
            "interval_hours": 2,
        },
        "agents": {a: {"enabled": True} for a in SUPPORTED_AGENTS},
    }


def detect_agent():
    """Auto-detect which agent is calling."""
    # Check OPENMEM_AGENT env var (highest priority)
    env_agent = os.environ.get("OPENMEM_AGENT", "").lower().strip()
    if env_agent and env_agent in SUPPORTED_AGENTS:
        return env_agent

    # Check agent-specific env vars
    env_map = {
        "qwen_code": ["QWEN_CODE_WORKSPACE", "QWEN_CODE_SESSION"],
        "claude_code": ["CLAUDE_CODE_WORKSPACE"],
        "cursor": ["CURSOR_WORKSPACE"],
        "vscode": ["VSCODE_CWD"],
        "windsurf": ["WINDSURF_WORKSPACE"],
        "codex_cli": ["CODEX_WORKSPACE"],
        "opencode": ["OPENCODE_WORKSPACE"],
        "antigravity_ide": ["ANTIGRAVITY_WORKSPACE"],
        "kilo_cli": ["KILO_WORKSPACE"],
    }

    for agent_name, env_vars in env_map.items():
        for var in env_vars:
            if os.environ.get(var):
                return agent_name

    # Check if running from a specific agent's workspace
    cwd = os.getcwd()
    path_indicators = {
        "qwen_code": [".qwen"],
        "claude_code": ["CLAUDE.md", ".claude"],
        "cursor": [".cursor"],
        "vscode": [".vscode"],
        "windsurf": [".windsurf"],
        "codex_cli": [".codex"],
        "opencode": [".opencode"],
        "antigravity_ide": [".antigravity"],
        "kilo_cli": [".kilo"],
        "openclaw": [".openclaw"],
    }

    for agent_name, indicators in path_indicators.items():
        for indicator in indicators:
            if os.path.exists(os.path.join(cwd, indicator)):
                return agent_name

    return "generic"


def cmd_status(args):
    """Show system status."""
    config = load_config()
    detected = detect_agent()

    print(f"\n{'='*60}")
    print(f"  OpenMem — Autonomous Memory System")
    print(f"{'='*60}")
    print(f"  Version:        {config.get('version', '2.0.0')}")
    print(f"  Detected Agent: {detected}")
    print(f"  Forced Agent:   {args.agent if args.agent else 'auto'}")
    print(f"  Data Directory: {DATA_DIR}")
    print(f"  Config:         {CONFIG_FILE}")
    print(f"{'='*60}")

    # Check component status
    print("\n  Components:")

    # Vector DB
    try:
        from memory_store.vector_db import get_vector_db
        db = get_vector_db()
        stats = db.get_stats()
        tables = stats.get("tables", [])
        print(f"    ✅ Vector DB:  {len(tables)} table(s): {', '.join(tables) if tables else 'empty'}")
    except Exception as e:
        print(f"    ❌ Vector DB:  {e}")

    # Memory Manager
    try:
        from memory_store.memory_manager import MemoryManager
        mm = MemoryManager()
        mm_stats = mm.get_stats()
        tiers = mm_stats.get("tiers", {})
        tier_info = ", ".join(f"{k}: {v['count']}" for k, v in tiers.items())
        print(f"    ✅ Memory Mgr: {tier_info if tier_info else 'no memories yet'}")
    except Exception as e:
        print(f"    ❌ Memory Mgr: {e}")

    # User Model
    try:
        from memory_store.user_model import UserModel
        um = UserModel()
        um_stats = um.get_stats()
        print(f"    ✅ User Model: {um_stats.get('total_facts_tracked', 0)} facts, "
              f"{um_stats.get('total_topics_tracked', 0)} topics")
    except Exception as e:
        print(f"    ❌ User Model: {e}")

    # Scheduler
    try:
        from learning_loop.scheduler import LearningScheduler
        scheduler = LearningScheduler()
        sched = scheduler.get_status()
        print(f"    ✅ Scheduler:   {sched.get('cycles_completed', 0)} cycles, "
              f"last: {sched.get('last_cycle', 'Never')}")
    except Exception as e:
        print(f"    ❌ Scheduler:   {e}")

    # Data directory
    if DATA_DIR.exists():
        size = sum(f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file())
        print(f"\n  Data: {size:,} bytes across {len(list(DATA_DIR.rglob('*')))} files")
    else:
        print(f"\n  Data: directory not created (run --install)")

    print()


def cmd_run_cycle(args):
    """Run a learning cycle."""
    print("[Launcher] Starting learning cycle...")
    try:
        from learning_loop.scheduler import LearningScheduler
        scheduler = LearningScheduler()
        report = scheduler.run_cycle(full=getattr(args, "full", False))

        print(f"\n  Duration: {report.get('duration_seconds', 0):.1f}s")
        print(f"  Success:  {'✅' if report.get('success') else '❌'}")

        phases = report.get("phases", {})
        for phase, data in phases.items():
            if isinstance(data, dict) and "skipped" not in data:
                summary = ", ".join(f"{k}: {v}" for k, v in data.items()
                                   if not isinstance(v, (list, dict)))
                print(f"  [{phase}] {summary}")

        if not report.get("success") and report.get("error"):
            print(f"\n  Error: {report['error']}")
    except Exception as e:
        print(f"\n  ❌ Cycle failed: {e}")
        import traceback
        traceback.print_exc()


def cmd_search(args):
    """Search memories."""
    if not args.query:
        print("Usage: launcher.py --search <query>")
        return

    try:
        from memory_store.vector_db import get_vector_db
        db = get_vector_db()
        query = " ".join(args.query)
        results = db.search(query, n_results=args.limit or 10)

        print(f"\n  🔍 Search: \"{query}\"")
        print(f"  Found: {len(results)} results\n")

        for i, r in enumerate(results, 1):
            content = r.get("content", "")[:150]
            print(f"    {i}. {content}")
            print(f"       [importance: {r.get('importance', 0):.2f}]")
            if r.get("tags"):
                print(f"       tags: {r['tags']}")
            print()
    except Exception as e:
        print(f"  ❌ Search failed: {e}")


def cmd_skill(args):
    """Install skill for an agent."""
    agent = args.skill
    if agent == "all":
        print("[Launcher] Installing skills for all agents...\n")
        for a in SUPPORTED_AGENTS:
            if a == "generic":
                continue
            _install_single_skill(a)
    else:
        _install_single_skill(agent)


def _install_single_skill(agent_name):
    """Install skill for a single agent."""
    try:
        from agents.base import get_adapter
        adapter = get_adapter(agent_name)
        if not adapter:
            print(f"  ⚠️ No adapter for: {agent_name}")
            return

        install_path = adapter.install_skill(str(OPENMEM_ROOT))
        if install_path:
            print(f"  ✅ {adapter.get_agent_name()}: skills → {install_path}")
        else:
            print(f"  ⚠️ {adapter.get_agent_name()}: install path not available")
    except Exception as e:
        print(f"  ❌ {agent_name}: {e}")


def cmd_agents(args):
    """List supported agents."""
    print("\n  Supported Agents:\n")
    for i, agent in enumerate(SUPPORTED_AGENTS, 1):
        try:
            from agents.base import get_adapter
            adapter = get_adapter(agent)
            name = adapter.get_agent_name() if adapter else agent
        except Exception:
            name = agent

        indicator = " ← DETECTED" if detect_agent() == agent else ""
        print(f"    {i}. {name} ({agent}){indicator}")
    print()


def cmd_config(args):
    """Show current config."""
    config = load_config()
    print(json.dumps(config, indent=2))


def cmd_daemon(args):
    """Start daemon mode."""
    print("[Launcher] Starting daemon...")
    try:
        from learning_loop.scheduler import LearningScheduler
        scheduler = LearningScheduler()

        interval = getattr(args, "interval", None)
        if interval:
            interval = float(interval)

        scheduler.start_daemon(interval_hours=interval)
        print(f"  ✅ Daemon running (interval: {interval or scheduler.config['interval_hours']}h)")
        print("  Press Ctrl+C to stop.\n")

        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop_daemon()
            print("\n  Daemon stopped.")
    except Exception as e:
        print(f"  ❌ Daemon failed: {e}")


def cmd_install(args):
    """Run installation."""
    from bin.install import OpenMemInstaller
    installer = OpenMemInstaller()
    installer.run_all()


def cmd_profile(args):
    """Show user profile."""
    try:
        from memory_store.vector_db import get_vector_db
        db = get_vector_db()
        profiles = db.get_all_user_profiles()

        print("\n  👤 User Profile\n")
        if not profiles:
            print("    No profile data yet. Keep interacting to build profile!")
            return

        for key, data in profiles.items():
            print(f"    {key}: {data['value']} (confidence: {data['confidence']:.0%})")
        print()
    except Exception as e:
        print(f"  ❌ Profile error: {e}")


def cmd_stats(args):
    """Show statistics."""
    try:
        from memory_store.vector_db import get_vector_db
        from learning_loop.scheduler import LearningScheduler
        from autonomous import get_optimizer, EvolutionEngine

        db = get_vector_db()
        db_stats = db.get_stats()
        scheduler = LearningScheduler()
        sched = scheduler.get_status()
        optimizer = get_optimizer()
        opt = optimizer.get_stats()
        evolution = EvolutionEngine()
        evo = evolution.get_stats()

        print(f"""
  {'='*50}
  OpenMem Statistics
  {'='*50}
  Database Tables:     {len(db_stats.get('tables', []))}
  Learning Cycles:     {sched.get('cycles_completed', 0)}
  Cycles Failed:       {sched.get('cycles_failed', 0)}
  Messages Indexed:    {sched.get('stats', {}).get('total_messages_indexed', 0)}
  Skills Generated:    {sched.get('stats', {}).get('skills_generated', 0)}

  Optimizer Entities:  {opt.get('total_entities', 0)}
  Matrix Size:         {opt.get('matrix_size', 0)}x{opt.get('matrix_size', 0)}

  Evolution Generation: {evo.get('generation', 0)}
  Population Size:     {evo.get('population_size', 0)}
  Best Fitness:        {evo.get('best_fitness', 0):.3f}
  {'='*50}
""")
    except Exception as e:
        print(f"  ❌ Stats error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="OpenMem Universal Launcher — Agent-Agnostic Memory System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bin/launcher.py                  # Auto-detect, show status
  python bin/launcher.py --agent qwen     # Force Qwen Code
  python bin/launcher.py --install        # Full installation
  python bin/launcher.py --run-cycle      # Run learning cycle
  python bin/launcher.py --search python  # Search memories
  python bin/launcher.py --skill cursor   # Install Cursor skill
  python bin/launcher.py --skill all      # Install all skills
  python bin/launcher.py --daemon         # Start daemon
  python bin/launcher.py --agents         # List supported agents
"""
    )

    parser.add_argument("--agent", choices=SUPPORTED_AGENTS, help="Force specific agent")
    parser.add_argument("--install", action="store_true", help="Run full installation")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--run-cycle", action="store_true", help="Run learning cycle")
    parser.add_argument("--full", action="store_true", help="Full re-index (with --run-cycle)")
    parser.add_argument("--search", nargs="+", metavar="Q", help="Search memories")
    parser.add_argument("--limit", type=int, default=10, help="Search result limit")
    parser.add_argument("--skill", metavar="AGENT", help="Install skill for agent (or 'all')")
    parser.add_argument("--daemon", action="store_true", help="Start daemon")
    parser.add_argument("--interval", help="Daemon interval (hours)")
    parser.add_argument("--config", action="store_true", help="Show config")
    parser.add_argument("--agents", action="store_true", help="List supported agents")
    parser.add_argument("--profile", action="store_true", help="Show user profile")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    # If no args given, show status
    if len(sys.argv) == 1:
        cmd_status(args)
        return 0

    # Dispatch
    commands = {
        "install": cmd_install,
        "status": cmd_status,
        "run_cycle": cmd_run_cycle,
        "search": cmd_search,
        "skill": cmd_skill,
        "daemon": cmd_daemon,
        "config": cmd_config,
        "agents": cmd_agents,
        "profile": cmd_profile,
        "stats": cmd_stats,
    }

    for arg_name, cmd_fn in commands.items():
        if getattr(args, arg_name, False) or (arg_name == "search" and args.search):
            try:
                cmd_fn(args)
                return 0
            except Exception as e:
                print(f"[Launcher] Error: {e}")
                import traceback
                traceback.print_exc()
                return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
