from event import Event

class Actions:
    """Shared action library for both Player and NPC."""
    
    @staticmethod
    def apply(world, agent, action_name, *args):
        """
        Apply an action for any agent (Player or NPC).
        
        Args:
            world: World instance
            agent: Agent instance (Player or NPC)
            action_name: "enter" | "sabo" | "report" | "kill"
            *args: additional arguments for the action
        
        Returns:
            Event object or None
        """
        if agent.state != "alive":
            return None
        
        if action_name == "enter":
            return Actions.enter(world, agent, *args)
        elif action_name == "sabo":
            return Actions.sabo(world, agent, *args)
        elif action_name == "report":
            return Actions.report(world, agent, *args)
        elif action_name == "kill":
            return Actions.kill(world, agent, *args)
        elif action_name == "idle":
            return Actions.idle(world, agent, *args)
        elif action_name == "task":
            return Actions.task(world, agent, *args)
        else:
            return None
    
    @staticmethod
    def enter(world, agent, target_room):
        """
        Move agent to target room.
        
        Args:
            world: World instance
            agent: Agent instance
            target_room: room name to move to
        
        Returns:
            Event object or None
        """
        if target_room not in world.rooms:
            return None
        
        agent.location = target_room
        # Movement is witnessed by agents at destination
        witnesses = [a.id for a in world.get_agents_at_location(target_room) 
                    if a.id != agent.id]
        visibility = "witnessed" if witnesses else "private"
        event = world.create_event("enter", agent.id, target_room, witnesses, visibility)
        agent.action = "enter"
        agent.behavior = "idle"  # Entering a room resets to idle
        return event
    
    @staticmethod
    def sabo(world, agent, sabo_type=None):
        """
        Perform sabotage action.
        
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
        agent.behavior = "sabo"
        return event
    
    @staticmethod
    def report(world, agent, info=None):
        """
        Make a public report (triggers voting).
        
        Args:
            world: World instance
            agent: Agent instance
            info: report information (optional)
        
        Returns:
            Event object
        """
        # Reports are public announcements - triggers voting
        witnesses = [a.id for a in world.get_alive_agents() if a.id != agent.id]
        event = world.create_event("report", agent.id, agent.location, witnesses, "public")
        agent.action = "report"
        agent.behavior = "voting"  # Report triggers voting
        
        # Trigger voting after report (voted agent is already marked dead in conduct_vote)
        voted_out = world.conduct_vote(agent.id)
        
        # After voting, reset behavior
        agent.behavior = "idle"
        
        return event
    
    @staticmethod
    def kill(world, agent, target_id):
        """
        Kill target agent.
        
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
        
        # If kill was witnessed, agent is caught
        if witnesses:
            if agent.id == world.player.id:
                print(f"Kill was witnessed! You are caught!")
            agent.state = "dead"
            world.result = "Caught"
        
        agent.behavior = "idle"  # After kill, reset to idle
        
        return event
    
    @staticmethod
    def idle(world, agent, duration=None):
        """
        Agent idles (does nothing).
        
        Args:
            world: World instance
            agent: Agent instance
            duration: how long to idle (optional, random if not provided)
        
        Returns:
            None (no event created for idle)
        """
        agent.action = "idle"
        agent.behavior = "idle"
        return None  # Idle doesn't create events
    
    @staticmethod
    def task(world, agent, duration=None):
        """
        Agent performs a task.
        
        Args:
            world: World instance
            agent: Agent instance
            duration: how long the task takes (optional)
        
        Returns:
            None (task doesn't create events, but updates behavior)
        """
        agent.action = "task"
        agent.behavior = "task"
        return None  # Task doesn't create events
