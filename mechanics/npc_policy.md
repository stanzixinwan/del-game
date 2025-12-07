# NPC Policy Design (Role-Specific)

This document specifies how to structure NPC decision-making logic with **role-specific policies** for a minimal single-player Among-Us-like game.

## Goals

- Separate **good** and **bad** agent behavior.
- Keep **speech (SAY)** and **action** logic inside `npc_policy.py`.
- Make it easy to extend with new roles or personality types later.

### good agent
report when one enters a location and find a dead agent
statement: declare self-role/ provide evidence/ make accusation


### bad agent
sabo whenever alone, takes time to react(stop sabo) when another one comes in
kill whenever alone with only one agent
statement: lie about self role/ false evidence

---

## Module Responsibilities

**`npc_policy.py`** should handle:

- Choosing **non-verbal actions** (move, task, sabo, kill, idle).
- Choosing **verbal actions** (SAY statements in the Voting Phase).
- Using:
  - `npc.knowledge.worlds`
  - `npc.knowledge.memory`
  - `npc.sus[...]`
  - `game_state` (phase, alive agents, etc.)

It should **not** own:

- Event data structures (`event.py`).
- Kripke/world models (`world.py`).
- Game loop (`main.py`).

---

## Core API

```python
def choose_action(npc, game_state):
    """
    Decide the next instant action for this NPC.
    Called each NPC turn during normal phases (non-voting).
    Returns an action object or enum (e.g. ENTER(room), TASK, SABO, KILL, IDLE).
    """

def choose_statement(npc, game_state):
    """
    Decide what the NPC says during the voting phase.
    Returns a Statement or None if the NPC stays silent.
    """
