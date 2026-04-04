#!/usr/bin/env python3
"""
LanceMem Self-Learning Skill for OpenClaw.
Autonomous memory system powered by LanceDB.

Usage as OpenClaw skill:
    /learn run      - Run a full learning cycle
    /learn status   - Show system status
    /learn patterns - Show discovered patterns
    /learn skills   - List auto-generated skills
    /learn search <query> - Semantic search over memories
    /learn stats    - Show LanceMem statistics
    /learn profile  - Show user profile
    /learn install  - Install LanceDB binary
    /learn init    - Initialize database

Install:
    python bin/lancedb_manager.py install
    python main.py init
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add LanceMem to path
LANCE_MEM_BASE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(LANCE_MEM_BASE))

# Core LanceMem modules
from memory_store.vector_db import get_vector_db, LanceDBVectorStore
from memory_store.memory_manager import MemoryManager
from memory_store.user_model import UserModel
from memory_store.skill_generator import SkillGenerator
from learning_loop.conversation_indexer import ConversationIndexer
from learning_loop.pattern_recognizer import PatternRecognizer
from learning_loop.reflection_engine import ReflectionEngine
from learning_loop.scheduler import LearningScheduler
from autonomous import get_optimizer, EvolutionEngine
from bin.lancedb_manager import LanceDBManager


def get_skill_context() -> dict:
    """Get context for skill execution."""
    return {
        "skill_name": "lance-self-learning",
        "skill_version": "2.0.0",
        "lance_mem_path": str(LANCE_MEM_BASE),
        "vector_db": "LanceDB",
        "timestamp": datetime.now().isoformat()
    }


# ===== Command Handlers =====

def cmd_run(args: list, context: dict) -> dict:
    """Run a full learning cycle."""
    scheduler = LearningScheduler()
    report = scheduler.run_cycle()

    return {
        "response": f"""🧠 **LanceMem Learning Cycle Complete**

⏱️ Duration: {report.get('duration_seconds', 0):.1f}s
📊 Messages indexed: {report.get('phases', {}).get('indexing', {}).get('messages_indexed', 0)}
🎯 Patterns found: {report.get('phases', {}).get('pattern_recognition', {}).get('patterns_found', 0)}
🛠️ Skills generated: {report.get('phases', {}).get('skill_generation', {}).get('skills_generated', 0)}
✅ Improvements made: {report.get('phases', {}).get('reflection', {}).get('improvements_completed', 0)}
🔄 Optimization cycle: {report.get('phases', {}).get('optimization', {}).get('pruned', 0)} pruned, {report.get('phases', {}).get('optimization', {}).get('strengthened', 0)} strengthened

{('❌ Error: ' + report.get('error', '')) if not report.get('success') else '✨ All phases completed successfully!'}""",
        "success": report.get("success", False),
        "data": report
    }


def cmd_status(args: list, context: dict) -> dict:
    """Show LanceMem system status."""
    manager = LanceDBManager()
    lance_status = manager.status()
    
    db = get_vector_db()
    db_stats = db.get_stats()
    
    scheduler = LearningScheduler()
    sched_status = scheduler.get_status()

    response = f"""📊 **LanceMem Status**

**LanceDB:**
- Installed: {'🟢 Yes' if lance_status['installed'] else '🔴 No'}
- Server: {'🟢 Running' if lance_status['server_running'] else '🔴 Stopped'}
- Tables: {', '.join(db_stats.get('tables', ['none']))}

**Scheduler:**
- Daemon: {'🟢 Running' if sched_status['daemon_running'] else '🔴 Stopped'}
- Last cycle: {sched_status.get('last_cycle') or 'Never'}
- Cycles: {sched_status.get('cycles_completed', 0)}

**Database:**
- Memories: {db_stats.get('lancedb_available', False) and 'LanceDB active' or 'SQLite fallback'}
- Embedder: {'🟢 Sentence-Transformers' if db_stats.get('embedder_available') else '🔴 Fallback mode'}"""

    return {
        "response": response,
        "success": True,
        "data": {
            "lance_status": lance_status,
            "db_stats": db_stats,
            "scheduler_status": sched_status
        }
    }


def cmd_install(args: list, context: dict) -> dict:
    """Install LanceDB binary."""
    manager = LanceDBManager()
    success = manager.install()
    
    if success:
        # Also initialize
        manager.init_database()
        
        response = """✅ **LanceDB Installed Successfully**

Binary installed to: bin/
Data stored at: data/lancedb_storage/

Next steps:
1. python main.py init      # Initialize database
2. python main.py run-cycle  # Run first learning cycle
3. python main.py daemon start  # Start autonomous daemon"""
    else:
        response = """❌ **Installation Failed**

Check:
- Internet connection
- GitHub access (for downloads)
- Write permissions to bin/

Manual install: pip install lancedb"""
    
    return {
        "response": response,
        "success": success
    }


def cmd_init(args: list, context: dict) -> dict:
    """Initialize LanceMem database."""
    manager = LanceDBManager()
    
    # Initialize database
    success = manager.init_database()
    
    if success:
        # Initialize vector store
        db = LanceDBVectorStore()
        db.optimize()
        
        response = """✅ **LanceMem Initialized**

Database ready at: data/lancedb_storage/
Vector index created.
Ready for autonomous operation.

Run `/learn run` to start learning!"""
    else:
        response = """❌ **Initialization Failed**

Make sure LanceDB is installed:
/learn install"""
    
    return {
        "response": response,
        "success": success
    }


def cmd_patterns(args: list, context: dict) -> dict:
    """Show discovered patterns."""
    recognizer = PatternRecognizer()
    patterns = recognizer.find_recurring_patterns(days_back=7)
    recommendations = recognizer.get_recommended_skills()

    if not patterns:
        return {
            "response": "🔍 No patterns discovered yet. Keep interacting to build patterns!",
            "success": True,
            "data": []
        }

    pattern_lines = []
    for i, p in enumerate(patterns[:10], 1):
        pattern_lines.append(f"{i}. **{p['type']}**: {p['pattern']}")
        pattern_lines.append(f"   Frequency: {p['frequency']}x | Confidence: {p.get('confidence', 0):.0%}")
        if p.get('recommendation'):
            pattern_lines.append(f"   → {p['recommendation']}")

    rec_lines = []
    for i, r in enumerate(recommendations[:5], 1):
        rec_lines.append(f"{i}. [{r['type']}] {r['trigger']} (freq: {r['frequency']})")

    response = f"""🔍 **Pattern Analysis (7 days)**

**Top Patterns:**
{chr(10).join(pattern_lines)}

**Skill Recommendations:**
{chr(10).join(rec_lines) if rec_lines else 'None yet — keep building patterns!'}"""

    return {
        "response": response,
        "success": True,
        "data": {"patterns": patterns, "recommendations": recommendations}
    }


def cmd_skills(args: list, context: dict) -> dict:
    """List auto-generated skills."""
    generator = SkillGenerator()
    skills = generator.get_generated_skills()
    stats = generator.get_stats()

    if not skills:
        return {
            "response": "🛠️ No auto-generated skills yet.\n\nRun `/learn run` to discover patterns and generate skills!",
            "success": True,
            "data": []
        }

    skill_lines = []
    for s in skills:
        skill_lines.append(f"- **{s['name']}**: {s.get('triggers', ['unknown'])[:3]}, used {s.get('usage_count', 0)}x")

    response = f"""🛠️ **Auto-Generated Skills** ({stats['total_skills_generated']} total)

{chr(10).join(skill_lines)}

Total uses: {stats['total_uses']}"""

    return {
        "response": response,
        "success": True,
        "data": skills
    }


def cmd_search(args: list, context: dict) -> dict:
    """Semantic search over memories."""
    if not args:
        return {
            "response": "🔍 Usage: `/learn search <query>`\n\nExample: `/learn search what is my project name`",
            "success": False,
            "error": "No query provided"
        }

    query = " ".join(args)
    db = get_vector_db()
    results = db.search(query, n_results=5)

    if not results:
        return {
            "response": f"🔍 No memories found for: **{query}**",
            "success": True,
            "data": []
        }

    result_lines = []
    for i, r in enumerate(results, 1):
        content = r.get('content', '')[:150]
        score = r.get('_distance', 'N/A')
        result_lines.append(f"{i}. {content}{'...' if len(r.get('content', '')) > 150 else ''}")
        result_lines.append(f"   [relevance: {score}]")

    response = f"""🔍 **Memory Search: "{query}"**

{chr(10).join(result_lines)}"""

    return {
        "response": response,
        "success": True,
        "data": results
    }


def cmd_stats(args: list, context: dict) -> dict:
    """Show LanceMem statistics."""
    optimizer = get_optimizer()
    evolution = EvolutionEngine()
    
    opt_stats = optimizer.get_stats()
    evo_stats = evolution.get_stats()

    response = f"""📈 **LanceMem Statistics**

**Optimization Matrix:**
- Entities tracked: {opt_stats.get('total_entities', 0)}
- Matrix size: {opt_stats.get('matrix_size', 0)}x{opt_stats.get('matrix_size', 0)}
- Prune threshold: {opt_stats.get('prune_threshold', 0.2)}

**Self-Evolution:**
- Generation: {evo_stats.get('generation', 0)}
- Population: {evo_stats.get('population_size', 0)}
- Best fitness: {evo_stats.get('best_fitness', 0):.3f}
- Avg fitness: {evo_stats.get('avg_fitness', 0):.3f}

**Entity Types:**"""

    by_type = opt_stats.get('by_type', {})
    for etype, data in by_type.items():
        response += f"\n- {etype}: {data.get('count', 0)} (avg perf: {data.get('avg_perf', 0):.2f})"

    return {
        "response": response,
        "success": True,
        "data": {
            "optimizer": opt_stats,
            "evolution": evo_stats
        }
    }


def cmd_profile(args: list, context: dict) -> dict:
    """Show user profile."""
    db = get_vector_db()
    profiles = db.get_all_user_profiles()
    
    model = UserModel()
    style = model.get_preferred_response_style()

    response = f"""👤 **User Profile**

**Communication Style:**
- Formality: {style.get('formal') and 'Formal' or 'Casual'}
- Verbosity: {style.get('max_length', 500) > 500 and 'Verbose' or 'Concise'}
- Emoji: {'Yes' if style.get('use_emoji') else 'No'}

**Tracked Facts:**"""

    if profiles:
        for key, data in profiles.items():
            response += f"\n- {key}: {data['value']} ({data['confidence']:.0%})"
    else:
        response += "\n- None yet (keep interacting!)"

    return {
        "response": response,
        "success": True,
        "data": {
            "profiles": profiles,
            "style": style
        }
    }


def cmd_optimize(args: list, context: dict) -> dict:
    """Run optimization cycle manually."""
    optimizer = get_optimizer()
    report = optimizer.run_optimization_cycle()

    response = f"""🔄 **Optimization Cycle Complete**

**Pruned:** {len(report.get('pruned', []))} entities
**Strengthened:** {len(report.get('strengthened', []))} entities
**Analyzed:** {report.get('analyzed', 0)} entities

**Pruned entities:**
{chr(10).join([f"- {p['entity_id']} (score: {p['prune_score']:.3f})" for p in report.get('pruned', [])[:5]]) or 'None'}

**Strengthened entities:**
{chr(10).join([f"- {s['entity_id']} (score: {s['new_score']:.3f})" for s in report.get('strengthened', [])[:5]]) or 'None'}"""

    return {
        "response": response,
        "success": True,
        "data": report
    }


def cmd_evolve(args: list, context: dict) -> dict:
    """Run evolution cycle manually."""
    evolution = EvolutionEngine()
    report = evolution.evolve()

    response = f"""🧬 **Evolution Cycle Complete**

**Generation:** {report.get('generation', 0)}
**Population:** {report.get('population_size', 0)}
**Avg Fitness:** {report.get('avg_fitness', 0):.3f}
**Best Fitness:** {report.get('best_fitness', 0):.3f}

**New entities:** {report.get('new_entities', 0)}
**Crossovers:** {report.get('crossovers', 0)}
**Mutations:** {report.get('mutations', 0)}
**Converged:** {'Yes ✅' if report.get('converged') else 'No ❌'}"""

    return {
        "response": response,
        "success": True,
        "data": report
    }


# ===== Command Registry =====

COMMANDS = {
    "run": cmd_run,
    "status": cmd_status,
    "install": cmd_install,
    "init": cmd_init,
    "patterns": cmd_patterns,
    "skills": cmd_skills,
    "search": cmd_search,
    "stats": cmd_stats,
    "profile": cmd_profile,
    "optimize": cmd_optimize,
    "evolve": cmd_evolve,
}


def execute(command: str, args: list, context: dict = None) -> dict:
    """
    Main entry point for the LanceMem OpenClaw skill.
    
    Args:
        command: Subcommand (run, status, search, etc.)
        args: Arguments for the command
        context: OpenClaw context dict (optional)
        
    Returns:
        dict with 'response' (str), 'success' (bool), optional 'data' (dict)
    """
    context = context or {}
    context.update(get_skill_context())

    if command not in COMMANDS:
        available = ", ".join(COMMANDS.keys())
        return {
            "response": f"""❓ Unknown command: {command}

Available commands:
{available}

Usage:
/learn run       - Run learning cycle
/learn status    - System status
/learn install   - Install LanceDB
/learn init     - Initialize database
/learn search <q> - Search memories
/learn patterns  - Show patterns
/learn skills    - List skills
/learn stats     - Statistics
/learn profile   - User profile
/learn optimize  - Run optimization
/learn evolve    - Run evolution""",
            "success": False,
            "error": f"Unknown command: {command}"
        }

    try:
        return COMMANDS[command](args, context)
    except Exception as e:
        import traceback
        return {
            "response": f"❌ Error in /learn {command}: {str(e)}\n\n_{traceback.format_exc()}_",
            "success": False,
            "error": str(e)
        }


# ===== CLI Entry Point =====

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("LanceMem Self-Learning Skill")
        print("Usage: python learner.py <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    result = execute(command, args)
    print(result["response"])
    sys.exit(0 if result.get("success") else 1)
