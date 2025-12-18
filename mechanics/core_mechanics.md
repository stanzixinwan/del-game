# Minimal Single-Player Among-Us-like Core Loop

## Action Types

### Instant Actions (produce events)
- ENTER(room)
- REPORT(info)
- KILL(agent)
- SAY(statement)
- SABO()
→ These create events and trigger belief updates.

if **Kill** happens, the killed agent state is 'dead', and stays in that location, to represent corpse. After some agent find it and report, the player's location is then set to none/unknown(whichever makes more sense), means the body has been removed to avoid duplicate report.

### Behavior States (ongoing)
- IDLE
- TASK
- VOTING
→ These do NOT create events; they modify what instant actions can occur.

## Language System (Minimal)

### Statement
statement = {
    predicate: "role" | "location" | "did",
    subject: agent_id,
    value: any,
    speaker: agent_id,
    timestamp: t
}

### SAY Action
SAY(predicate, subject, value)
→ produces public event
→ append to all agents' memory as ("heard", statement)

### Memory Use
NPC checks:
- consistency with its own memory
- consistency with observed events
- effect on world belief weight

### Soft Evidence
Statement does not delete worlds.
It only adjusts belief weights or NPC suspicion.

### NPC Speech Generation
In voting phase:
- accuse: SAY("role", target, "bad")
- defend: SAY("location", self, last_location)
- claim innocence: SAY("did", self, "task")


## Agent
- id
- state (alive, dead)
- behavior
- role (good, bad)
- location
- action
- knowledge

agent.behavior = idle | task | voting
once an agent takes action, its behavior state updates

## NPC
NPC decides to take action after a (random for now) duration of time, not only when events happen

- sus
sus[agent] = {
    "player": 0,
    "npc1": 0,
    ...
}
intially 0 for every agent, add or deduct when witness certain event(e.g. sabo) where no worlds elimination happen

## Vote
player vote interative
npc vote
    good agents: for every other id, get_num where the id_role=bad -> if 1 max sum, vote for the id; if more than 1 max sum, compare agent.sus["id"]; else can't decide, skip
cause belief updates
    game not over: dead npc number >= bad agent number (now just 1) -> eliminate world where all dead agent(s) is/are bad
    if I know my role is good and get voted by agent n, add belief to n being a bad role

# Kripke Model
Knowledge[agent] = {
    "worlds": [world1, world2, ...], 
    "memory": [MemoryItem1, MemoryItem2 ...]
}
(Initialize with all possible worlds, eliminate the world where itself's role is wrong)
(for now just do all cases of 1 bad agent)

# World representation
world = {
    "player": "bad",
    "npc1": "good",
    ...
} 
(each world should contain all the agents)

# MemoryItem
MemoryItem = {
    "event_id": ...,
    "type": "saw" | "heard" | "said" | "deduced",
    "content": ...,
    "timestamp": ...
}

# Event representation
event = {
    "action": "kill" | "sabo" | "enter" | "report",
    "actor": "player" | "npc1",
    "location": "room2",
    "witnesses": ["npc2", "npc3"],
    "timestamp": 128.3,
    "visibility": "private" | "witnessed" | "public"
}

## Knowledge Update
Knowledge is per-agent
Private → update(actor)
Witnessed → update(actor + observers)
Public → update(all agents)
Delete certain worlds

## Loop
init → player action → event (public/private/witnessed) → belief update → NPC decision → repeat
report → vote → continue if game not over
### Gameover
    Bad agent win: num bad >= num good
    bad agent lost: got most voted -> state=dead | get caught (for now only achieved by Kill being witnessed) 
