"""
NPC Policy Design (Role-Specific)

This module handles NPC decision-making logic with role-specific policies.
It separates good and bad agent behavior, and handles both non-verbal actions
and verbal actions (statements) during voting phase.
"""

import random
from statement import Statement
from agent import Player as PlayerClass


def choose_action(npc, world):
    """
    Decide the next instant action for this NPC.
    Called each NPC turn during normal phases (non-voting).
    
    Uses role-specific policies:
    - Good agents: task, move, report when they identify bad agents
    - Bad agents: kill, sabotage, etc.
    
    Args:
        npc: NPC instance
        world: World instance (game state)
    
    Returns:
        ("action", args) tuple or None
        Examples: ("report", None), ("enter", "Engine"), ("task", None), ("idle", None)
    """
    # Route to role-specific policy
    if npc.role == "good":
        return _choose_action_good(npc, world)
    elif npc.role == "bad":
        return _choose_action_bad(npc, world)
    else:
        # Default fallback
        return ("idle", None)


def _choose_action_good(npc, world):
    """
    Action policy for good agents.
    
    Good agents:
    - Report when entering a location and finding a dead agent (corpse)
    - Report when they identify a bad agent (worlds <= threshold)
    - Move closer to suspicious agents
    - Do tasks
    - Move around
    - Idle
    """
    # 1. If entering a location and finding a dead agent, report immediately
    # According to npc_policy.md: "report when one enters a location and find a dead agent"
    dead_agents = world.get_dead_agents_at_location(npc.location)
    if dead_agents:
        # Found a corpse - report it
        return ("report", None)
    
    # 2. If NPC believes (via possible worlds) that a bad agent is likely AND worlds <= threshold:
    #       return ("report", None)
    if npc.knowledge["worlds"]:
        # Check if we have identified a bad agent in any world
        has_bad = False
        for world_state in npc.knowledge["worlds"]:
            if any(role == "bad" for role in world_state.values()):
                has_bad = True
                break
        
        # If we have identified a bad agent and have few enough worlds, report
        if has_bad and len(npc.knowledge["worlds"]) <= 2:
            return ("report", None)
    
    # 3. If suspicion[player] is high:
    #       return ("enter", room_closer_to_player)
    if hasattr(npc, 'sus') and world.player is not None and isinstance(world.player, PlayerClass) and world.player.state == "alive":
        player_sus = npc.sus.get(world.player.id, 0)
        if player_sus > 0.5:  # High suspicion threshold
            # Move closer to player (or to player's location if connected)
            player_location = world.player.location
            if player_location in world.rooms and player_location != npc.location:
                # Check if player's location is connected
                if world.are_connected(npc.location, player_location):
                    return ("enter", player_location)
            # Otherwise move to a random connected room
            connected_rooms = world.get_connected_rooms(npc.location)
            if connected_rooms:
                return ("enter", random.choice(connected_rooms))
    
    # 3b. If no player, check suspicion of bad agents instead
    if world.player is None and hasattr(npc, 'sus'):
        # Find most suspicious agent
        max_sus = -1
        most_suspicious = None
        for agent_id, sus_value in npc.sus.items():
            agent = world._get_agent_by_id(agent_id)
            if agent and agent.state == "alive" and agent.id != npc.id and sus_value > max_sus:
                max_sus = sus_value
                most_suspicious = agent
        
        if most_suspicious and max_sus > 0.5:
            # Move closer to suspicious agent (if connected)
            target_location = most_suspicious.location
            if target_location in world.rooms and target_location != npc.location:
                if world.are_connected(npc.location, target_location):
                    return ("enter", target_location)
            # Otherwise try a connected room
            connected_rooms = world.get_connected_rooms(npc.location)
            if connected_rooms:
                return ("enter", random.choice(connected_rooms))
    
    # 4. Else: with small probability, move or do task
    if random.random() < 0.8:
        # 50% chance to move
        if random.random() < 0.5:
            # Only move to connected rooms
            connected_rooms = world.get_connected_rooms(npc.location)
            if connected_rooms:
                return ("enter", random.choice(connected_rooms))
        else:
            # 50% of that 50% = 25% chance to do task
            return ("task", None)
    
    # 5. Default: idle
    # Most of the time, NPCs are idle
    return ("idle", None)


def _choose_action_bad(npc, world):
    """
    Action policy for bad agents.
    
    Bad agents:
    - Kill when opportunity arises (same location, no witnesses)
    - Sabotage to create chaos
    - Move strategically
    - Blend in (task/idle)
    """
    # For now, bad NPCs use a simple strategy
    # TODO: Implement more sophisticated bad agent behavior
    
    # 1. Check if we can kill someone (same location, no other witnesses)
    alive_agents = world.get_alive_agents()
    agents_at_location = [a for a in alive_agents 
                         if a.location == npc.location and a.id != npc.id]
    
    # If alone with a target, consider killing
    if len(agents_at_location) == 1:
        target = agents_at_location[0]
        if target.role == "good":  
            return ("kill", target.id)
    
    # 3. Move or task (blend in)
    if random.random() < 0.3:
        if random.random() < 0.5:
            # Only move to connected rooms
            connected_rooms = world.get_connected_rooms(npc.location)
            if connected_rooms:
                return ("enter", random.choice(connected_rooms))
        else:
            return ("task", None)
    
    # 4. Default: idle
    return ("idle", None)


def choose_statement(npc, world):
    """
    Decide what the NPC says during the voting phase.
    
    According to core_mechanics.md, NPCs can:
    - accuse: SAY("role", target, "bad")
    - defend: SAY("location", self, last_location)
    - claim innocence: SAY("did", self, "task")
    
    Args:
        npc: NPC instance
        world: World instance (game state)
    
    Returns:
        Statement object or None if the NPC stays silent
    """
    # Route to role-specific statement policy
    if npc.role == "good":
        return _choose_statement_good(npc, world)
    elif npc.role == "bad":
        return _choose_statement_bad(npc, world)
    else:
        return None


def _choose_statement_good(npc, world):
    """
    Statement policy for good agents during voting phase.
    
    Good agents can:
    - Accuse: SAY("role", target, "bad") when they have evidence
    - Defend: SAY("location", self, last_location) if accused
    - Claim innocence: SAY("did", self, "task")
    """
    # Check if NPC is being accused (high sus from others)
    # For now, use a simple heuristic: if we have a strong suspect, accuse them
    if npc.knowledge["worlds"]:
        # Find the most likely bad agent based on world counts
        agent_scores = {}
        all_agents = world.get_all_agents()
        
        for agent in all_agents:
            if agent.id == npc.id or agent.state != "alive":
                continue
            
            # Count worlds where this agent is bad
            count = 0
            for world_state in npc.knowledge["worlds"]:
                if world_state.get(agent.id) == "bad":
                    count += 1
            
            agent_scores[agent.id] = count
        
        if agent_scores:
            max_score = max(agent_scores.values())
            if max_score > 0:
                # Find agent(s) with max score
                candidates = [aid for aid, score in agent_scores.items() if score == max_score]
                
                # If we have a clear suspect, accuse them
                if len(candidates) == 1 and max_score >= len(npc.knowledge["worlds"]) * 0.5:
                    target_id = candidates[0]
                    if random.random() < 0.7:  # 70% chance to accuse
                        return Statement("role", target_id, "bad", npc.id)
                
                # If we have high suspicion, accuse based on sus values
                elif len(candidates) > 1:
                    # Use sus values to break tie
                    max_sus = -1
                    best_target = None
                    for candidate_id in candidates:
                        sus_value = npc.sus.get(candidate_id, 0)
                        if sus_value > max_sus:
                            max_sus = sus_value
                            best_target = candidate_id
                    
                    if best_target and max_sus > 0.5 and random.random() < 0.6:
                        return Statement("role", best_target, "bad", npc.id)
    
    # Defend: if someone accused us (high sus from others pointing to us)
    # For now, we'll occasionally defend ourselves
    if random.random() < 0.2:  # 20% chance to defend
        return Statement("location", npc.id, npc.location, npc.id)
    
    # Claim innocence: occasionally claim we were doing tasks
    if random.random() < 0.2:  # 20% chance
        return Statement("did", npc.id, "task", npc.id)
    
    # Most of the time, stay silent
    return None


def _choose_statement_bad(npc, world):
    """
    Statement policy for bad agents during voting phase.
    
    Bad agents can:
    - Accuse others (deflection)
    - Defend themselves
    - Claim innocence
    - Lie about their actions
    """
    alive_agents = world.get_alive_agents()
    good_agents = [a for a in alive_agents if a.role == "good" and a.id != npc.id]
    
    if not good_agents:
        return None
    
    # 1. If under suspicion, deflect by accusing someone else
    # Check if we're a likely suspect in other agents' worlds
    if random.random() < 0.6:  # 60% chance to deflect
        target = random.choice(good_agents)
        return Statement("role", target.id, "bad", npc.id)
    
    # 2. Defend: claim we were at a location
    if random.random() < 0.3:  # 30% chance
        return Statement("location", npc.id, npc.location, npc.id)
    
    # 3. Claim innocence: claim we were doing tasks
    if random.random() < 0.2:  # 20% chance
        return Statement("did", npc.id, "task", npc.id)
    
    # Stay silent otherwise
    return None
