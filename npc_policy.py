"""
NPC Policy Design (Role-Specific)

This module handles NPC decision-making logic with role-specific policies.
It separates good and bad agent behavior, and handles both non-verbal actions
and verbal actions (statements) during voting phase.

NOTE: All functions in this module are designed exclusively for NPC instances.
They will raise TypeError if called with non-NPC agents.
"""

import random
from statement import Statement
from agent import Player as PlayerClass, NPC


def choose_action(npc, world):
    """
    Decide the next instant action for this NPC.
    Called each NPC turn during normal phases (non-voting).
    
    Uses role-specific policies:
    - Good agents: task, move, report when they identify bad agents
    - Bad agents: kill, sabotage, etc.
    
    Args:
        npc: NPC instance (must be an NPC, not Player or base Agent)
        world: World instance (game state)
    
    Returns:
        ("action", args) tuple or None
        Examples: ("report", None), ("enter", "Engine"), ("task", None), ("idle", None)
    
    Raises:
        TypeError: if npc is not an NPC instance
    """
    # Type check: ensure this is an NPC instance
    if not isinstance(npc, NPC):
        raise TypeError(f"choose_action() requires an NPC instance, got {type(npc).__name__}")
    
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
    Action policy for good NPC agents.
    
    Good NPCs:
    - Report when entering a location and finding a dead agent (corpse)
    - Report when they identify a bad agent (worlds <= threshold)
    - Move closer to suspicious agents
    - Do tasks
    - Move around
    - Idle
    
    Args:
        npc: NPC instance (must be good role)
        world: World instance (game state)
    """
    # Ensure this is an NPC with sus tracking
    if not isinstance(npc, NPC) or not hasattr(npc, 'sus'):
        return ("idle", None)
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
    Action policy for bad NPC agents.
    
    Bad NPCs:
    - Kill when opportunity arises (same location, no witnesses)
    - Sabotage to create chaos
    - Move strategically
    - Blend in (task/idle)
    
    Args:
        npc: NPC instance (must be bad role)
        world: World instance (game state)
    """
    # Ensure this is an NPC
    if not isinstance(npc, NPC):
        return ("idle", None)
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
        npc: NPC instance (must be an NPC, not Player or base Agent)
        world: World instance (game state)
    
    Returns:
        Statement object or None if the NPC stays silent
    
    Raises:
        TypeError: if npc is not an NPC instance
    """
    # Type check: ensure this is an NPC instance
    if not isinstance(npc, NPC):
        raise TypeError(f"choose_statement() requires an NPC instance, got {type(npc).__name__}")
    
    # Route to role-specific statement policy
    if npc.role == "good":
        return _choose_statement_good(npc, world)
    elif npc.role == "bad":
        return _choose_statement_bad(npc, world)
    else:
        return None


def _choose_statement_good(npc, world):
    """
    Statement policy for good NPC agents during voting phase.
    
    Good NPCs can:
    - Accuse: SAY("role", target, "bad") when they have evidence
    - Defend: SAY("location", self, last_location) if accused
    - Claim innocence: SAY("did", self, "task")
    
    Args:
        npc: NPC instance (must be good role with sus tracking)
        world: World instance (game state)
    """
    # Ensure this is an NPC with sus tracking
    if not isinstance(npc, NPC) or not hasattr(npc, 'sus'):
        return None
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
    Statement policy for bad NPC agents during voting phase.
    
    Bad NPCs can:
    - Accuse others (deflection)
    - Defend themselves
    - Claim innocence
    - Lie about their actions
    
    Args:
        npc: NPC instance (must be bad role)
        world: World instance (game state)
    """
    # Ensure this is an NPC
    if not isinstance(npc, NPC):
        return None
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


def choose_vote(npc, world):
    """
    Decide who the NPC votes for during voting phase.
    
    Role-specific voting strategies:
    - Good NPCs: Vote based on possible worlds (count worlds where agent is bad)
    - Bad NPCs: Vote strategically to avoid suspicion, rarely vote for themselves
    
    Args:
        npc: NPC instance (must be an NPC, not Player or base Agent)
        world: World instance (game state)
    
    Returns:
        Agent ID to vote for, or None to skip vote
    
    Raises:
        TypeError: if npc is not an NPC instance
    """
    # Type check: ensure this is an NPC instance
    if not isinstance(npc, NPC):
        raise TypeError(f"choose_vote() requires an NPC instance, got {type(npc).__name__}")
    
    # Route to role-specific voting policy
    if npc.role == "good":
        return _choose_vote_good(npc, world)
    elif npc.role == "bad":
        return _choose_vote_bad(npc, world)
    else:
        return None


def _choose_vote_good(npc, world):
    """
    Voting policy for good NPC agents.
    
    Good NPCs vote based on:
    - Count worlds where each agent is bad
    - Vote for agent with highest count
    - Use sus values to break ties
    
    Args:
        npc: NPC instance (must be good role with sus tracking)
        world: World instance (game state)
    
    Returns:
        Agent ID to vote for, or None to skip vote
    """
    # Ensure this is an NPC with sus tracking
    if not isinstance(npc, NPC) or not hasattr(npc, 'sus'):
        return None
    
    # Count worlds where each agent is bad
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
    
    if not agent_scores:
        return None
    
    # Vote for agent with highest count
    max_score = max(agent_scores.values())
    if max_score > 0:
        # Find agent(s) with max score
        candidates = [aid for aid, score in agent_scores.items() if score == max_score]
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            # Tie: compare sus values
            best_candidate = None
            max_sus = -1
            sus_values = [npc.sus.get(cid, 0) for cid in candidates]
            for candidate_id in candidates:
                sus_value = npc.sus.get(candidate_id, 0)
                if sus_value > max_sus:
                    max_sus = sus_value
                    best_candidate = candidate_id
            
            # Only return best_candidate if there's a unique max sus > 0
            # If all sus are equal (including all 0), skip vote
            if max_sus > 0 and sus_values.count(max_sus) == 1:
                return best_candidate
            # If all sus are equal (all 0 or all same), skip vote
            return None
    
    return None


def _choose_vote_bad(npc, world):
    """
    Voting policy for bad NPC agents.
    
    Bad NPCs vote strategically:
    - Avoid voting for themselves (mostly)
    - Vote for good agents to eliminate them
    - May vote randomly to avoid patterns
    - Rarely vote for themselves (only if no other option)
    
    Args:
        npc: NPC instance (must be bad role)
        world: World instance (game state)
    
    Returns:
        Agent ID to vote for, or None to skip vote
    """
    # Ensure this is an NPC
    if not isinstance(npc, NPC):
        return None
    
    alive_agents = world.get_alive_agents()
    # Get all other agents (exclude self)
    candidates = [a for a in alive_agents if a.id != npc.id and a.state == "alive"]
    
    if not candidates:
        # No one else to vote for, skip vote
        return None
    
    # Bad NPCs prefer to vote for good agents
    good_agents = [a for a in candidates if a.role == "good"]
    
    if good_agents:
        # Prefer voting for good agents
        # Could use some strategy here, but for now pick randomly from good agents
        # with slight preference for agents with lower suspicion (less likely to be suspected)
        if random.random() < 0.8:  # 80% chance to vote for a good agent
            # Pick a random good agent
            return random.choice(good_agents).id
        else:
            # 20% chance to vote for any agent (including bad if any)
            return random.choice(candidates).id
    else:
        # No good agents left, vote for any other agent
        # Bad NPCs might vote for other bad agents if it helps them survive
        return random.choice(candidates).id
