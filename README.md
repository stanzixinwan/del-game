# DEL-Game: Dynamic Epistemic Logic in Multi-Agent Deduction

A multi-agent deduction game system inspired by "werewolf" and "among us", where AI players use **Dynamic Epistemic Logic (DEL)** and **Kripke models** to reason about hidden information and make strategic decisions.

## Core Logic: DEL and Kripke Models

### Kripke Model for Knowledge Representation

Each agent maintains a **Kripke model** of possible worlds, representing their epistemic uncertainty about the true game state.

#### World Structure

A **world** is a dictionary mapping agent IDs to their roles:

```python
world_state = {
    "player": "bad",
    "npc0": "good",
    "npc1": "good",
    "npc2": "good"
}
```

Each agent's knowledge consists of:
- **`knowledge["worlds"]`**: A list of possible world states consistent with what the agent knows
- **`knowledge["memory"]`**: A sequence of `MemoryItem` objects representing observed events

#### World Initialization

At game start, each agent initializes with all possible worlds where:
- Exactly one agent is "bad" (the impostor)
- The agent's own role matches their actual role (they know themselves)

**Example**: With 4 agents (1 bad, 3 good), each good agent starts with 3 possible worlds (one where each other agent could be bad). The bad agent starts with 1 world (where they are bad).

### Dynamic Epistemic Logic (DEL) Update Cycle

The system implements a rigorous **DEL update cycle** that distinguishes between:

#### 1. Hard Knowledge (S5 Logic)

**Certainty: `FACT`** - Information observed directly or from public events.

When an agent receives information with `Certainty.FACT`:
- **World Elimination**: Remove all worlds inconsistent with the fact
- **Example**: Seeing a KILL action → eliminate all worlds where the killer is "good"

**Event Handlers (FACT)**:
- **KILL (observed)**: Actor must be "bad" → eliminate worlds where actor is "good"
- **VOTE_RESULT (public)**: 
  - If game continues after vote → voted agent was "good" → eliminate worlds where they're "bad"
  - If I was voted out and I'm good → voters might be "bad" → eliminate worlds where voters are "good"

#### 2. Soft Belief (KD45 Logic)

**Certainty: `UNCERTAIN`** - Information from hearsay or statements.

When an agent receives information with `Certainty.UNCERTAIN`:
- **No World Elimination**: Worlds remain possible
- **Suspicion Update**: Adjust `sus` (suspicion) scores for agents
- **Example**: Hearing "X is bad" → slightly increase `sus[X]` but don't eliminate worlds

**Event Handlers (UNCERTAIN)**:
- **SAY (heard)**: If statement claims "role is bad" → increase target's suspicion by 0.1
- **SABO (heard about)**: Increase actor's suspicion by 0.2

### MemoryItem System

The system uses `MemoryItem` objects to wrap events, tracking:
- **Source Type**: `"observation"` (directly seen) or `"hearsay"` (heard from others)
- **Certainty**: Automatically determined:
  - `observation` → `Certainty.FACT`
  - `hearsay` → `Certainty.UNCERTAIN`
- **Event Reference**: Links to the original global event

This separation allows agents to distinguish between what they know for certain and what they've merely heard.

### DEL Update Cycle Implementation

```
Event Occurs
    ↓
Create MemoryItem (determines Certainty)
    ↓
Agent.update_knowledge(memory_item)  [Store in memory]
    ↓
Agent.update_belief(memory_item, world_context)
    ↓
Branch on Certainty:
    ├─ FACT → _update_belief_hard_knowledge()
    │         └─ Eliminate inconsistent worlds
    │
    └─ UNCERTAIN → _update_belief_soft_belief()
                  └─ Update suspicion scores (sus)
```

### Statement System

Agents can make formal logical statements during the voting phase:

- **Predicates**: `"role"`, `"location"`, `"did"`
- **Format**: `SAY(predicate, subject, value)`
- **Example**: `SAY("role", "npc1", "bad")` → "I claim npc1's role is bad"

Statements are treated as **soft evidence** (UNCERTAIN) and do not eliminate worlds directly. They influence suspicion scores and can be evaluated for consistency with observed facts.

## Key Components

### Agent Knowledge Structure

```python
agent.knowledge = {
    "worlds": [
        {"player": "bad", "npc0": "good", ...},  # World 1
        {"player": "good", "npc0": "bad", ...},  # World 2
        ...
    ],
    "memory": [
        MemoryItem(observation, FACT, ...),
        MemoryItem(hearsay, UNCERTAIN, ...),
        ...
    ]
}
```

### Event Visibility Types

Events have different visibility, affecting how they're stored:

- **`private`**: Only the actor observes (as FACT)
- **`witnessed`**: Actor and witnesses observe (as FACT)
- **`public`**: All agents know:
  - Actor observes as FACT (observation)
  - Others receive as UNCERTAIN (hearsay)

### Voting and Belief Updates

After voting:
1. Vote result creates a `vote_result` event (public FACT)
2. All agents process this event:
   - If game continues → voted agent was "good" → eliminate worlds where they're "bad"
   - If I was voted out and I'm good → eliminate worlds where my voters are "good"
3. Additional logic: If enough agents are dead, eliminate worlds where all dead agents are "bad" (contradicts game state)

## Implementation Highlights

### Robust World Filtering

- Checks for empty worlds list before filtering
- Progressive filtering for multiple constraints (e.g., multiple voters)
- Early termination if no worlds remain

### Separation of Concerns

- **Memory Storage**: `MemoryItem` objects in `knowledge["memory"]`
- **Belief Updates**: DEL update cycle in `update_belief()`
- **Action Selection**: NPC policy in `npc_policy.py`
- **Event Creation**: World manages event creation and distribution

## Quick Start

### Player Mode

```bash
python main.py
# Choose mode 1
```

### Simulation Mode (All NPCs)

```bash
python main.py
# Choose mode 2
```

## Architecture Overview

```
main.py
  └─ World (game state, event creation)
      ├─ Agent.update_knowledge() [Store MemoryItem]
      ├─ Agent.update_belief() [DEL Update Cycle]
      │   ├─ Hard Knowledge (FACT) → World Elimination
      │   └─ Soft Belief (UNCERTAIN) → Sus Update
      └─ NPC Policy (action selection)
          ├─ choose_action() [Non-verbal actions]
          └─ choose_statement() [Verbal actions in voting]
```

## Core Files

- **`agent.py`**: Agent class with Kripke model and DEL update cycle
- **`world.py`**: World state, event creation, world initialization
- **`memory.py`**: `MemoryItem` and `Certainty` enum
- **`statement.py`**: Formal statement system for SAY actions
- **`npc_policy.py`**: Role-specific NPC decision making
- **`actions.py`**: Shared action library (instant actions + behavior states)
- **`mechanics/`**: Design documentation

## Design Philosophy

This implementation emphasizes:

1. **Rigorous DEL Semantics**: Clear separation between hard knowledge (world elimination) and soft belief (suspicion)
2. **Epistemic Uncertainty**: Agents maintain multiple possible worlds until evidence eliminates them
3. **Source Tracking**: MemoryItems distinguish observation from hearsay
4. **Centralized Belief Updates**: All belief logic in `Agent.update_belief()`

The system provides a foundation for more sophisticated epistemic reasoning, including:
- Multi-agent knowledge (common knowledge)
- Nested beliefs ("I know that you know...")
- Trust models and statement verification
- More complex world elimination rules
