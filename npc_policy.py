import random

def choose_action(npc, world):
    """
    NPC chooses action based on knowledge and suspicion.
    
    Args:
        npc: NPC instance
        world: World instance
    
    Returns:
        ("action", args) tuple or None
        Examples: ("report", None), ("enter", "Engine"), None
    """
    # 1. If NPC believes (via possible worlds) that a bad agent is likely AND worlds <= threshold:
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
    
    # 2. If suspicion[player] is high:
    #       return ("enter", room_closer_to_player)
    if hasattr(npc, 'sus') and world.player.state == "alive":
        player_sus = npc.sus.get(world.player.id, 0)
        if player_sus > 0.5:  # High suspicion threshold
            # Move closer to player (or to player's location if possible)
            player_location = world.player.location
            if player_location in world.rooms and player_location != npc.location:
                return ("enter", player_location)
            # Otherwise move to a random room
            available_rooms = [r for r in world.rooms if r != npc.location]
            if available_rooms:
                return ("enter", random.choice(available_rooms))
    
    # 3. Else: with small probability, move or do task
    if random.random() < 0.3:
        # 30% chance to move
        if random.random() < 0.5:
            available_rooms = [r for r in world.rooms if r != npc.location]
            if available_rooms:
                return ("enter", random.choice(available_rooms))
        else:
            # 50% of that 30% = 15% chance to do task
            return ("task", None)
    
    # 4. Default: idle
    # Most of the time, NPCs are idle
    return ("idle", None)
