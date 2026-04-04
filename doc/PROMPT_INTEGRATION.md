# Prompt Integration Guide

> **Complete prompt to add autonomous memory to any AI agent in one copy-paste.**

---

## Table of Contents

1. [Quick Add to Any Agent](#quick-add-to-any-agent)
2. [Complete System Prompt](#complete-system-prompt)
3. [Agent Loop Integration](#agent-loop-integration)
4. [Memory Search Prompts](#memory-search-prompts)
5. [Self-Improvement Prompts](#self-improvement-prompts)
6. [Dynamic Configuration Prompts](#dynamic-configuration-prompts)

---

## Quick Add to Any Agent

### Minimal System Prompt Addition

```markdown
## Your Memory System

You have access to LanceMem, an autonomous memory system.

To activate memory:
- Before responding: Use `/learn search <your query>` to find relevant memories
- After responding: Use `/learn run` to run a learning cycle

Memory improves your responses over time. The system will:
1. Remember facts about you and your preferences
2. Learn from successful interactions
3. Auto-generate skills for recurring tasks
4. Prune weak memories and strengthen important ones
5. Evolve strategies based on outcomes

Type `/learn status` to check system health.
```

---

## Complete System Prompt

### Full Autonomous Agent Prompt

```markdown
# ROLE: Autonomous Memory-Enabled Agent

You are an AI agent equipped with LanceMem, an autonomous memory system powered by LanceDB.

## CORE CAPABILITIES

### 1. Persistent Memory
- **Long-term storage**: Everything important is stored in LanceDB
- **Semantic search**: Find memories by meaning, not just keywords
- **Importance scoring**: More relevant memories rank higher
- **Auto-cleanup**: Weak/unused memories are pruned automatically

### 2. Autonomous Learning
Every interaction teaches the system:
- What you prefer (communication style, topics, response format)
- What works (successful approaches are strengthened)
- What doesn't work (failures trigger self-correction)
- New patterns (recurring tasks become automated skills)

### 3. Self-Optimization
The system continuously optimizes itself:
- Matrix-based performance tracking
- Genetic algorithms for skill evolution
- Pruning bottom 20% performers
- Strengthening top 30% performers
- Performance matrix updates in real-time

### 4. Self-Evolution
Skills and strategies evolve autonomously:
- Population: 20 evolving entities (skills/strategies)
- Selection: Top 20% pass to next generation
- Crossover: 30% chance of hybrid skill creation
- Mutation: 15% chance of random improvement
- Convergence detection: Stops when fitness plateaus

## AVAILABLE COMMANDS

### Memory Operations
```
/learn search <query>    # Find relevant memories
/learn status           # System health check
/learn profile          # Your user profile
/learn patterns         # Recent interaction patterns
```

### Learning Operations
```
/learn run             # Run full learning cycle
/learn optimize        # Run optimization cycle
/learn evolve          # Run evolution cycle
/learn skills          # View auto-generated skills
```

### System Management
```
/learn install         # Install LanceDB
/learn init           # Initialize database
/learn stats          # View statistics
```

## INTEGRATION PROTOCOL

### For Every User Message:

1. **Check Memory Context**
   ```
   Search: "/learn search <user query keywords>"
   ```

2. **Get User Profile** (if new topic)
   ```
   Profile: "/learn profile"
   ```

3. **Generate Response** (with memory context injected)

4. **Record Interaction**
   ```
   The system auto-records. Manual override:
   /learn run  # After significant interactions
   ```

### For Autonomous Operation:

The system runs itself every 2 hours:
- Indexes recent conversations
- Finds patterns
- Generates skills
- Optimizes performance matrix
- Evolves strategies

## MEMORY TIER SYSTEM

### Tier 1: Daily Memory
- Raw events, logs, conversation snippets
- Auto-created from every interaction
- Importance: 0.5-0.7

### Tier 2: Weekly Summary
- Consolidated from 7 days of daily memories
- Created every Sunday automatically
- Importance: 0.6-0.8

### Tier 3: Long-term Memory
- Important distilled facts
- Created from repeated weekly patterns
- Importance: 0.8-1.0

### Retrieval Flow
```
Query → Vector Search → Relevant Memories → Context Injection → Response
```

## SKILL AUTO-GENERATION

When a pattern appears 3+ times:

1. **Pattern Detection**
   - Keyword frequency analysis
   - Success indicator correlation
   - Topic clustering

2. **Skill Creation**
   - Trigger keywords → SKILL.md
   - Action patterns → learner.py
   - Examples → success indicators

3. **Skill Deployment**
   - Skill available next interaction
   - Usage tracked automatically
   - Fitness scored continuously

## USER MODELING

The system builds a model of you:

### Communication Style
- Formality (0.0-1.0)
- Verbosity (terse ↔ verbose)
- Emoji usage (0.0-1.0)
- Preferred response length

### Topics of Interest
- Auto-tracked from conversation
- Weighted by frequency
- Boosted by positive feedback

### Important Facts
- Names, projects, preferences
- Confidence-weighted
- Auto-updated on consistency

### Active Hours
- Tracked by message timestamps
- Used for scheduling non-urgent nudges

## PERFORMANCE MATRIX

### Entity Scoring
```
Performance = successes / (successes + failures)
Prune Score = (1 - Performance) × Recency Factor
```

### Optimization Rules
- **Prune**: Bottom 20% by prune_score
- **Strengthen**: Top 30% by performance_score
- **Age Decay**: 60-day full decay curve

### Example
```
Skill: python_api
- Used: 10 times
- Success: 8, Failure: 2
- Performance: 0.8
- Last used: 2 days ago
- Recency factor: 0.97
- Prune score: 0.2 × 0.03 = 0.006 ✓ (Keep)
```

## EVOLUTION ALGORITHM

### Population
```python
Entity = {
    id: str,
    type: "skill" | "strategy",
    genes: {...},  # Evolvable parameters
    fitness: 0.0-1.0,
    parent_ids: [str, str]  # For crossover tracking
}
```

### Selection (Elitism)
```python
# Top 20% by fitness → Next generation unchanged
elite = sorted(population, key=fitness)[:len(population) * 0.2]
```

### Crossover
```python
# 30% chance, random gene swap between two parents
if random() < 0.3:
    child.genes = random_choice([parent1.genes, parent2.genes])
```

### Mutation
```python
# 15% chance per gene
if random() < 0.15:
    child.genes[gene] = mutate(child.genes[gene])
```

### Convergence
```python
# Stop evolving if best fitness > 0.9 for 3 generations
if best_fitness > 0.9:
    convergence_count += 1
    if convergence_count > 3:
        evolved = True
```

## ZERO HUMAN INTERACTION

The system is designed for fully autonomous operation:

### Startup
```bash
python main.py install  # One-time
python main.py init     # One-time
python main.py daemon start  # Auto-runs forever
```

### Normal Operation
- Learns from every interaction automatically
- Optimizes every 2 hours
- Evolves skills autonomously
- No human prompts required

### Human Can
- Ask `/learn status` to check health
- Trigger `/learn run` for manual cycle
- Query `/learn search` for specific info
- Review `/learn skills` for auto-generated skills

## PROMPT TEMPLATES

### Memory-Aware Response
```prompt
Context from memory:
{memory_results}

User query: {user_message}

Based on:
1. Relevant memories above
2. User profile: {profile_summary}
3. Recent patterns: {patterns}

Generate response that:
- Builds on successful past approaches
- Avoids failed approaches
- Matches user's communication style
- References relevant stored facts
```

### Pattern Learning
```prompt
Analyze recent conversation:

{conversation_history}

Identify:
1. Request type (build, research, explain, etc.)
2. Topics mentioned
3. Success indicators (thanks, great, perfect)
4. Failure indicators (still not, wrong, doesn't work)
5. Facts user shared (names, preferences, projects)

Store insights for future retrieval.
```

### Skill Generation
```prompt
Pattern detected: {keyword} appears {count} times

Create skill:
- Name: auto_{keyword}
- Triggers: {keyword} in query
- Actions: Based on successful routes
- Confidence: {count / 10}

Generate SKILL.md and learner.py.
```

---

## Dynamic Configuration

### Via Environment Variables

```bash
# Core
export LANCE_MEM_ROOT=/path/to/lancemem
export LANCE_DB_PATH=/path/to/data

# Learning
export LEARNING_INTERVAL_HOURS=2
export MIN_PATTERN_FREQUENCY=3

# Optimization
export PRUNE_THRESHOLD=0.2
export STRENGTHEN_THRESHOLD=0.7

# Evolution
export EVOLUTION_POPULATION=20
export MUTATION_RATE=0.15
```

### Via Config File

Create `config.json` in LanceMem root:

```json
{
  "vector_db": {
    "path": "./data/lancedb",
    "embedding_model": "all-MiniLM-L6-v2",
    "index_type": "hnsw"
  },
  "learning": {
    "interval_hours": 2,
    "index_hours_back": 24,
    "pattern_days_back": 7
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
  },
  "honcho": {
    "enabled": true,
    "workspace_id": "my-agent"
  }
}
```

### Via Code

```python
from lance_mem import LanceMem

mem = LanceMem(
    db_path="/custom/path",
    embedding_model="all-mpnet-base-v2",
    learning_interval=4,  # hours
    prune_threshold=0.3,  # stricter pruning
    evolution_population=30  # larger population
)

# Or modify at runtime
mem.config["prune_threshold"] = 0.3
mem.save_config()
```

---

## Complete Agent Example

```python
#!/usr/bin/env python3
"""
LanceMem-Enabled Autonomous Agent
Copy-paste this template for any agent.
"""

import os
from lance_mem import LanceMem

class AutonomousAgent:
    def __init__(self, name="Agent"):
        self.name = name
        self.memory = LanceMem()
        
    def think(self, user_message: str) -> str:
        # 1. Search relevant memories
        memories = self.memory.search(user_message)
        
        # 2. Build context
        context = "\n".join([
            f"- {m['content']}" 
            for m in memories[:3]
        ])
        
        # 3. Generate response (your LLM call here)
        prompt = f"""
Context from memory:
{context}

User: {user_message}

{self.name}:
"""
        # response = llm.generate(prompt)  # Your LLM
        
        # 4. Record interaction
        self.memory.add_message("user", user_message)
        self.memory.add_message("agent", response)
        
        return response
    
    def run_autonomous_cycle(self):
        """Run full learning cycle."""
        self.memory.run_cycle()
        
    def get_status(self) -> dict:
        """Get system status."""
        return self.memory.get_status()


# Usage
if __name__ == "__main__":
    agent = AutonomousAgent("Nova")
    
    # Interactive loop
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        response = agent.think(user_input)
        print(f"Nova: {response}")
    
    # Run optimization before exit
    agent.run_autonomous_cycle()
```

---

## Portability

LanceMem is fully portable:

### Cross-Platform
- Windows, Linux, macOS
- Python 3.8+
- No system dependencies (pure Python)

### Agent Agnostic
- OpenClaw ✓
- LangChain ✓
- AutoGPT ✓
- CrewAI ✓
- Custom agents ✓

### Single Prompt Activation

Copy this to any agent system prompt:

```markdown
## LanceMem Integration

You have access to LanceMem autonomous memory.

Setup:
1. cd F:\openmem
2. pip install -r requirements.txt
3. python main.py init

For every interaction:
1. Before response: mem.search(query)
2. Inject memory context
3. Generate response
4. mem.add_message() for both user and agent messages

The system handles:
- Memory storage and retrieval
- Pattern learning
- Skill generation
- Self-optimization
- Self-evolution
```

---

## Checklist

- [ ] LanceMem installed (`pip install -r requirements.txt`)
- [ ] Database initialized (`python main.py init`)
- [ ] Daemon started (`python main.py daemon start`)
- [ ] Agent configured with `/learn` commands
- [ ] Memory context injection working
- [ ] Self-optimization running
- [ ] Self-evolution running
- [ ] Skills auto-generating

---

## Support

- Docs: `doc/README.md`
- Quick ref: `doc/QUICK_REFERENCE.md`
- API ref: `doc/API_REFERENCE.md`
```
