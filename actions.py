from event import Event
from statement import Statement

class Actions:
    """
    Shared action library for both Player and NPC.
    
    Actions are separated into:
    - Instant Actions (produce events): ENTER, REPORT, KILL, SAY, SABO
    - Behavior States (ongoing, no events): IDLE, TASK, VOTING
    """
    
    # Instant actions (produce events)
    INSTANT_ACTIONS = ["enter", "report", "kill", "say", "sabo"]
    
    # Behavior states (modify behavior, no events)
    BEHAVIOR_STATES = ["idle", "task", "voting"]
    
    @staticmethod
    def apply(world, agent, action_name, *args):
        """
        Apply an action for any agent (Player or NPC).
        
        Args:
            world: World instance
            agent: Agent instance (Player or NPC)
            action_name: instant action or behavior state name
            *args: additional arguments for the action
        
        Returns:
            Event object for instant actions, None for behavior states
        """
        if agent.state != "alive":
            return None
        
        # Instant actions (produce events)
        if action_name == "enter":
            return Actions.enter(world, agent, *args)
        elif action_name == "sabo":
            return Actions.sabo(world, agent, *args)
        elif action_name == "report":
            return Actions.report(world, agent, *args)
        elif action_name == "kill":
            return Actions.kill(world, agent, *args)
        elif action_name == "say":
            return Actions.say(world, agent, *args)
        
        # Behavior states (no events, just modify behavior)
        elif action_name == "idle":
            return Actions.set_idle(world, agent, *args)
        elif action_name == "task":
            return Actions.set_task(world, agent, *args)
        elif action_name == "voting":
            return Actions.set_voting(world, agent, *args)
        
        else:
            return None
    
    # ========== Instant Actions (produce events) ==========
    
    @staticmethod
    def enter(world, agent, target_room):
        """
        ENTER instant action - Move agent to target room (produces event).
        Only allows movement to directly connected rooms.
        
        Args:
            world: World instance
            agent: Agent instance
            target_room: room name to move to
        
        Returns:
            Event object or None (if invalid room or not connected)
        """
        # Check if room exists (handle both dict and list for backward compatibility)
        room_names = list(world.rooms.keys()) if isinstance(world.rooms, dict) else world.rooms
        if target_room not in room_names:
            return None
        
        # Check if target room is connected to current location
        current_location = agent.location
        if current_location and not world.are_connected(current_location, target_room):
            # Not directly connected - movement not allowed
            return None
        
        # Update room tracking before moving
        old_location = agent.location
        if old_location and old_location in world.rooms:
            world.rooms[old_location].remove_agent(agent)
        
        agent.location = target_room
        
        # Update room tracking after moving
        if target_room in world.rooms:
            world.rooms[target_room].add_agent(agent)
        
        # Movement is witnessed by agents at destination
        witnesses = [a.id for a in world.get_agents_at_location(target_room) 
                    if a.id != agent.id]
        visibility = "witnessed" if witnesses else "private"
        event = world.create_event("enter", agent.id, target_room, witnesses, visibility)
        agent.action = "enter"
        agent.behavior = "idle"  # Entering a room resets to idle
        
        # Check for dead agents (corpses) at the new location
        # Good agents should report when finding a dead agent
        dead_agents = world.get_dead_agents_at_location(target_room)
        if dead_agents and hasattr(agent, 'role') and agent.role == "good":
            # Good agent found a corpse - will report in next action decision
            # This is handled by npc_policy, but we could trigger it here if needed
            pass
        
        return event
    
    @staticmethod
    def sabo(world, agent, sabo_type=None):
        """
        SABO instant action - Perform sabotage (produces event).
        
        Args:
            world: World instance
            agent: Agent instance
            sabo_type: type of sabotage (optional)
        
        Returns:
            Event object
        """
        # Sabotage might be witnessed by agents in same location
        witnesses = [a.id for a in world.get_agents_at_location(agent.location) 
                    if a.id != agent.id]
        visibility = "witnessed" if witnesses else "private"
        event = world.create_event("sabo", agent.id, agent.location, witnesses, visibility)
        agent.action = "sabo"
        agent.behavior = "idle"  # Reset to idle after sabotage action
        return event
    
    @staticmethod
    def report(world, agent, info=None):
        """
        REPORT instant action - Make a public report (produces event, triggers voting).
        If reporting a dead body, removes the corpse after reporting.
        
        Args:
            world: World instance
            agent: Agent instance
            info: report information (optional)
        
        Returns:
            Event object
        """
        # Check if reporting a dead body at current location
        dead_agents = world.get_dead_agents_at_location(agent.location)
        
        # Reports are public announcements - triggers voting
        witnesses = [a.id for a in world.get_alive_agents() if a.id != agent.id]
        event = world.create_event("report", agent.id, agent.location, witnesses, "public")
        agent.action = "report"

        
        # If reporting a dead body, remove the corpse(s) to avoid duplicate reports
        # Set location to None to represent body removal
        for dead_agent in dead_agents:
            # Store location before removal to ensure correct room reference
            corpse_location = dead_agent.location
            # Remove from room tracking
            if corpse_location and corpse_location in world.rooms:
                world.rooms[corpse_location].remove_agent(dead_agent)
            # Set location to None to mark corpse as removed
            dead_agent.location = None
        
        # Trigger voting after report (now async - starts meeting phase)
        world.start_meeting(agent.id)
        # Note: behavior will remain "voting" during meeting phase
        # It will be reset to "idle" when meeting completes (handled in update_meeting)
        
        return event
    
    @staticmethod
    def kill(world, agent, target_id):
        """
        KILL instant action - Kill target agent (produces event).
        
        Args:
            world: World instance
            agent: Agent instance
            target_id: id of target agent to kill
        
        Returns:
            Event object or None
        """
        target = world._get_agent_by_id(target_id)
        if not target or target.state != "alive":
            return None
        
        # Kill might be witnessed by agents in same location
        witnesses = [a.id for a in world.get_agents_at_location(agent.location) 
                    if a.id != agent.id and a.id != target_id]
        visibility = "witnessed" if witnesses else "private"
        event = world.create_event("kill", agent.id, agent.location, witnesses, visibility)
        
        # Kill the target
        target.state = "dead"
        agent.action = "kill"
        
        # Update room tracking (target is now dead, should be in dead_agents)
        if target.location and target.location in world.rooms:
            world.rooms[target.location].remove_agent(target)
            world.rooms[target.location].add_agent(target)  # Re-add as dead agent
        
        # If kill was witnessed, witnesses observe it as FACT (hard knowledge)
        # This will trigger epistemic updates in _update_belief_hard_knowledge:
        # - Witnesses will eliminate all worlds where the killer is "good"
        # - The event is already created with "witnessed" visibility above,
        #   which creates MemoryItems with FACT certainty for witnesses
        # - No immediate game over - let the epistemic reasoning handle it
        if witnesses:
            print(f"Kill was witnessed by: {', '.join(witnesses)}")
            print(f"  → Witnesses now know {agent.id} is bad (FACT)")
        
        agent.behavior = "idle"  # After kill, reset to idle
        
        return event
    
    @staticmethod
    def say(world, agent, predicate, subject, value):
        """
        SAY instant action - Agent makes a statement (produces public event).
        
        Args:
            world: World instance
            agent: Agent instance
            predicate: "role" | "location" | "did"
            subject: agent_id that the statement is about
            value: the value/claim (e.g., "bad", "Engine", "task")
        
        Returns:
            Event object
        """
        # Create Statement object
        statement = Statement(predicate, subject, value, agent.id)
        
        # SAY produces a public event according to spec
        witnesses = [a.id for a in world.get_alive_agents() if a.id != agent.id]
        event = world.create_event("say", agent.id, agent.location, witnesses, "public", statement=statement)
        agent.action = "say"
        agent.behavior = "idle"  # After saying, reset to idle
        return event
    
    # ========== Behavior States (do NOT produce events) ==========
    
    @staticmethod
    def set_idle(world, agent, duration=None):
        """
        Set agent to idle behavior state.
        Behavior states do NOT create events; they modify what instant actions can occur.
        
        Args:
            world: World instance
            agent: Agent instance
            duration: how long to idle (optional)
        
        Returns:
            None (behavior states don't create events)
        """
        agent.behavior = "idle"
        agent.action = "idle"
        return None
    
    @staticmethod
    def set_task(world, agent, duration=None):
        """
        Set agent to task behavior state.
        Behavior states do NOT create events; they modify what instant actions can occur.
        
        Args:
            world: World instance
            agent: Agent instance
            duration: how long the task takes (optional)
        
        Returns:
            None (behavior states don't create events)
        """
        agent.behavior = "task"
        agent.action = "task"
        return None
    
    @staticmethod
    def set_voting(world, agent, duration=None):
        """
        Set agent to voting behavior state.
        Behavior states do NOT create events; they modify what instant actions can occur.
        
        Args:
            world: World instance
            agent: Agent instance
            duration: how long voting lasts (optional)
        
        Returns:
            None (behavior states don't create events)
        """
        agent.behavior = "voting"
        agent.action = "voting"
        return None
