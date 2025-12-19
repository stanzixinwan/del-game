from agent import Agent, NPC, Player
from event import Event
from memory import MemoryItem
from room import Room
import time
import random
from enum import Enum
from itertools import combinations

class GamePhase(Enum):
    """Game phase enumeration."""
    PHASE_PLAYING = "playing"  # Normal movement/action phase
    PHASE_MEETING = "meeting"  # Voting/meeting phase

class World:
    """World representation with id_roles."""
    
    def __init__(self, num_npcs=4, seed=None, rooms=["A", "B", "C", "D"], player=None, npcs=None, connections=None):
        """
        Initialize the game world.
        
        Args:
            num_npcs: number of NPC agents (used only if npcs is None)
            seed: random seed for reproducibility
            rooms: list of room names (default: ["A", "B", "C", "D"])
            player: Player instance (default: creates new Player with role="bad")
            npcs: list of NPC instances (default: creates num_npcs NPCs with role="good")
            connections: dict mapping room -> list of connected rooms (default: creates a connected graph)
        """
        if seed is not None:
            random.seed(seed)
        
        # Initialize Room objects
        if connections is not None:
            # Create Room objects with provided connections
            self.rooms = {name: Room(name, connections.get(name, [])) for name in rooms}
            # Ensure bidirectional connections
            for room_name, room in self.rooms.items():
                for connected_name in room.connected_rooms:
                    if connected_name in self.rooms:
                        if not self.rooms[connected_name].is_connected_to(room_name):
                            self.rooms[connected_name].add_connection(room_name)
            # Keep connections dict for backward compatibility
            self.connections = connections
        else:
            # Create Room objects with default connections
            self.rooms = self._initialize_rooms(rooms)
            # Build connections dict from Room objects for backward compatibility
            self.connections = {name: room.get_connected_rooms() for name, room in self.rooms.items()}
        
        # Set player (can be None for simulation mode with all NPCs)
        if player is False:  # Explicit False means no player
            self.player = None
        elif player is not None:
            self.player = player
        else:
            initial_location = list(self.rooms.keys())[0] if self.rooms else "Storage"
            self.player = Player("player", role="bad", location=initial_location)
        
        # Set NPCs
        if npcs is not None:
            self.npcs = npcs
        else:
            # Create NPCs with random locations from available rooms
            room_names = list(self.rooms.keys())
            self.npcs = [NPC(f"npc{i}", role="good", location=random.choice(room_names)) for i in range(num_npcs)]
        
        # Register all agents with their rooms
        self._register_agents_in_rooms()
        
        self.result = None
        self.turn = 0
        self.current_time = 0.0  # Current game time
        self.event_history = []  # Global event history
        
        # Game phase state machine
        self.phase = GamePhase.PHASE_PLAYING  # Current game phase
        self.meeting_timer = 0.0  # Timer for meeting phase progression
        self.meeting_step = 0  # Current step in meeting (0=statements, 1=voting, 2=result)
        self.meeting_queue = []  # Queue of agents who need to speak/vote
        self.meeting_reporter_id = None  # ID of agent who triggered the meeting
        self.meeting_statement_timer = 0.0  # Timer for individual statement delays
        self.meeting_next_statement_time = 2.0  # Time between statements (2 seconds)
        self.meeting_room = "E"  # Room E is the meeting room
        self.original_locations = {}  # Store original locations before meeting (agent_id -> location)
        
        # Automatic meeting scheduling
        self.last_meeting_time = 0.0  # Time when last meeting started
        self.meeting_interval = 10.0  # Seconds between automatic meetings
        
        # Initialize all possible worlds and sus for all agents
        self._initialize_all_worlds()
        self._initialize_sus()
        self._initialize_npc_times()
    
    def _initialize_rooms(self, room_names):
        """
        Initialize Room objects with T-shaped connections.
        Room B is the central hub connected to all other rooms.
        Other rooms only connect to B.
        
        Args:
            room_names: list of room name strings (must have at least 2 rooms)
        
        Returns:
            dict mapping room name -> Room object
        """
        # Create Room objects first (no connections yet)
        rooms = {name: Room(name, []) for name in room_names}
        
        # Set up T-shaped layout: B (second room) is central hub
        if len(room_names) >= 2:
            b = room_names[1]  # B is the central hub (second room)
            other_rooms = [r for r in room_names if r != b]
            
            # Room B connects to all other rooms (central hub)
            for other_room in other_rooms:
                rooms[b].add_connection(other_room)
                # Other rooms connect to B
                rooms[other_room].add_connection(b)
        # For 1 room or empty, no connections needed
        
        return rooms
    
    def _register_agents_in_rooms(self):
        """Register all agents with their current rooms."""
        for agent in self.get_all_agents():
            if agent.location and agent.location in self.rooms:
                self.rooms[agent.location].add_agent(agent)
    
    def _update_room_agents(self):
        """Update Room objects to reflect current agent locations."""
        # Clear all rooms
        for room in self.rooms.values():
            room.agents = []
            room.dead_agents = []
        
        # Add agents to their current rooms
        for agent in self.get_all_agents():
            if agent.location and agent.location in self.rooms:
                self.rooms[agent.location].add_agent(agent)
    
    
    def are_connected(self, room1, room2):
        """
        Check if two rooms are directly connected.
        
        Args:
            room1: source room name
            room2: target room name
        
        Returns:
            True if rooms are directly connected, False otherwise
        """
        # Use Room object if available, fallback to connections dict
        if room1 in self.rooms:
            return self.rooms[room1].is_connected_to(room2)
        if hasattr(self, 'connections') and room1 in self.connections:
            return room2 in self.connections[room1]
        return False
    
    def get_connected_rooms(self, room):
        """
        Get list of rooms directly connected to the given room.
        
        Args:
            room: room name
        
        Returns:
            List of connected room names, empty list if room not found
        """
        # Use Room object if available, fallback to connections dict
        if room in self.rooms:
            return self.rooms[room].get_connected_rooms()
        if hasattr(self, 'connections'):
            return self.connections.get(room, [])
        return []
    
    def _initialize_all_worlds(self):
        """
        Initialize all possible worlds for each agent.
        
        Good agents: Know their own role (good), so they consider all possible combinations
        of bad agents among the other agents.
        
        Bad agents: Know all bad agents (including themselves), so they only have
        one world where all bad agents are correctly identified.
        """
        all_agents = self.get_all_agents()
        all_agent_ids = [a.id for a in all_agents]
        
        # Identify all bad agents
        bad_agent_ids = [a.id for a in all_agents if a.role == "bad"]
        num_bad = len(bad_agent_ids)
        
        for agent in all_agents:
            worlds = []
            
            if agent.role == "good":
                # Good agent: Knows they are good, considers all combinations of bad agents among others
                other_agent_ids = [aid for aid in all_agent_ids if aid != agent.id]
                
                # Generate all possible combinations of bad agents from the other agents
                # Number of bad agents to choose = num_bad (since we know the total number)
                if num_bad > 0 and len(other_agent_ids) >= num_bad:
                    for bad_combination in combinations(other_agent_ids, num_bad):
                        # Create a world where these agents are bad
                        world_state = {}
                        for aid in all_agent_ids:
                            if aid == agent.id:
                                # Agent knows they are good
                                world_state[aid] = "good"
                            elif aid in bad_combination:
                                # This agent is bad in this world
                                world_state[aid] = "bad"
                            else:
                                # This agent is good in this world
                                world_state[aid] = "good"
                        worlds.append(world_state)
                elif num_bad == 0:
                    # No bad agents - only one world where everyone is good
                    world_state = {aid: "good" for aid in all_agent_ids}
                    worlds.append(world_state)
            
            elif agent.role == "bad":
                # Bad agent: Knows all bad agents (including themselves)
                # Only one world where all bad agents are correctly identified
                world_state = {}
                for aid in all_agent_ids:
                    if aid in bad_agent_ids:
                        world_state[aid] = "bad"
                    else:
                        world_state[aid] = "good"
                worlds.append(world_state)
            
            agent.knowledge["worlds"] = worlds
    
    def _initialize_sus(self):
        """Initialize sus for all NPCs (0 for every agent)."""
        all_agent_ids = [a.id for a in self.get_all_agents()]
        for npc in self.npcs:
            npc.sus = {aid: 0 for aid in all_agent_ids}
    
    def _initialize_npc_times(self):
        """Initialize next_action_time for all NPCs (random initial delay)."""
        for npc in self.npcs:
            # Random delay between 1-5 seconds for initial action
            npc.next_action_time = self.current_time + random.uniform(1.0, 5.0)
    
    def get_all_agents(self):
        """Get all agents (player + NPCs)."""
        if self.player is not None and isinstance(self.player, Player):
            return [self.player] + self.npcs
        else:
            return self.npcs
    
    def get_alive_agents(self):
        """Get all alive agents."""
        return [a for a in self.get_all_agents() if a.state == "alive"]
    
    def create_event(self, action, actor, location, witnesses=None, visibility="private", statement=None):
        """
        Create and process an event.
        Creates MemoryItems for agents based on how they observed the event.
        
        Args:
            action: action type
            actor: agent id performing action
            location: location of event
            witnesses: list of witness ids (None for private)
            visibility: "private" | "witnessed" | "public"
            statement: Statement object (only for "say" actions)
        
        Returns:
            Event object
        """
        event = Event(action, actor, location, witnesses, visibility, statement=statement)
        self.event_history.append(event)
        
        # Update knowledge based on visibility
        # MemoryItems wrap Event objects and track source_type (observation/hearsay)
        if visibility == "private":
            # Only the actor knows - they directly observed (performed) the action
            actor_agent = self._get_agent_by_id(actor)
            if actor_agent:
                memory_item = MemoryItem(event, "observation")
                actor_agent.update_knowledge(memory_item)
                # Actor directly observes their own action, so update beliefs
                actor_agent.update_belief(memory_item, self)
        elif visibility == "witnessed":
            # Actor and witnesses directly observe the event
            actor_agent = self._get_agent_by_id(actor)
            if actor_agent:
                # Actor directly observes their own action
                memory_item = MemoryItem(event, "observation")
                actor_agent.update_knowledge(memory_item)
                # Actor directly observes their own action, so update beliefs
                actor_agent.update_belief(memory_item, self)
            
            if witnesses:
                for witness_id in witnesses:
                    witness_agent = self._get_agent_by_id(witness_id)
                    if witness_agent:
                        # Witness directly observes (sees) the event
                        memory_item = MemoryItem(event, "observation")
                        witness_agent.update_knowledge(memory_item)
                        witness_agent.update_belief(memory_item, self)
        elif visibility == "public":
            # All agents know, but observation vs hearsay differs
            for agent in self.get_alive_agents():
                if agent.id == actor:
                    # Actor directly observes (performed) the action
                    memory_item = MemoryItem(event, "observation")
                else:
                    # Others hear about it from the actor (hearsay)
                    memory_item = MemoryItem(event, "hearsay", source_id=actor)
                
                agent.update_knowledge(memory_item)
                agent.update_belief(memory_item, self)
        
        return event
    
    def _get_agent_by_id(self, agent_id):
        """Get agent by id."""
        if self.player is not None and isinstance(self.player, Player) and agent_id == self.player.id:
            return self.player
        for npc in self.npcs:
            if npc.id == agent_id:
                return npc
        return None
    
    def get_agents_at_location(self, location):
        """Get all alive agents at a given location."""
        # Use Room object if available
        if location in self.rooms:
            return self.rooms[location].get_agents(alive_only=True)
        # Fallback to old method
        return [a for a in self.get_alive_agents() if a.location == location]
    
    def get_dead_agents_at_location(self, location):
        """Get all dead agents (corpses) at a given location."""
        # Use Room object if available
        if location in self.rooms:
            return self.rooms[location].get_dead_agents()
        # Fallback to old method
        return [a for a in self.get_all_agents() if a.state == "dead" and a.location == location]
    
    def start_meeting(self, reporter_id):
        """
        Start a meeting/voting phase after a report.
        Sets up the meeting phase, teleports all agents to central location, and initializes queues.
        
        Args:
            reporter_id: ID of agent who triggered the meeting (reported)
        """
        # Prevent starting a new meeting if already in a meeting
        if self.phase == GamePhase.PHASE_MEETING:
            print(f"[Warning] Meeting already in progress, ignoring new meeting request from {reporter_id}")
            return
        
        # Set phase to meeting
        self.phase = GamePhase.PHASE_MEETING
        self.meeting_reporter_id = reporter_id
        self.meeting_timer = 0.0
        self.meeting_statement_timer = 0.0
        self.meeting_step = 0  # 0 = statements phase, 1 = voting phase, 2 = result phase
        
        # Get all alive agents
        alive_agents = self.get_alive_agents()
        
        # Store original locations before teleporting to meeting room
        self.original_locations = {}
        for agent in alive_agents:
            self.original_locations[agent.id] = agent.location
        
        # Teleport all agents to meeting room (room E)
        meeting_location = self.meeting_room if self.meeting_room in self.rooms else None
        if meeting_location:
            for agent in alive_agents:
                old_location = agent.location
                if old_location and old_location in self.rooms:
                    self.rooms[old_location].remove_agent(agent)
                agent.location = meeting_location
                if meeting_location in self.rooms:
                    self.rooms[meeting_location].add_agent(agent)
        
        # Initialize meeting queue (all alive agents will speak in order)
        self.meeting_queue = alive_agents.copy()
        
        # Update last meeting time (reset automatic meeting timer)
        self.last_meeting_time = self.current_time
        
        print(f"\n=== MEETING STARTED (Reported by {reporter_id}) ===")
        print(f"All agents gathered at {meeting_location} (meeting room)")
    
    def update_meeting(self, delta_time):
        """
        Update meeting phase logic (called when phase == PHASE_MEETING).
        Handles phased meeting progression: statements -> voting -> results.
        
        Args:
            delta_time: time elapsed since last update
        """
        if self.phase != GamePhase.PHASE_MEETING:
            return
        
        self.meeting_timer += delta_time
        self.meeting_statement_timer += delta_time
        
        from npc_policy import choose_statement
        from actions import Actions
        
        # Step 0: Statements Phase - agents speak one at a time (every 2 seconds)
        if self.meeting_step == 0:
            # Check if it's time for next statement (every 2 seconds)
            if self.meeting_statement_timer >= self.meeting_next_statement_time and self.meeting_queue:
                agent = self.meeting_queue.pop(0)
                
                if isinstance(agent, NPC):
                    # NPCs use choose_statement
                    statement = choose_statement(agent, self)
                    if statement:
                        # NPC makes statement using SAY action
                        Actions.say(self, agent, statement.predicate, statement.subject, statement.value)
                        print(f"  {agent.id} says: {statement}")
                    else:
                        print(f"  {agent.id} stays silent")
                else:
                    # Player can make statement (for now, we'll skip interactive input in async mode)
                    # In async mode, players could make statements via UI - for now they stay silent
                    # This could be enhanced later with UI prompts
                    print(f"  {agent.id} stays silent (async mode)")
                
                # Reset timer for next statement
                self.meeting_statement_timer = 0.0
            
            # If queue is empty, move to voting phase
            if not self.meeting_queue:
                print("\n--- Voting Phase ---")
                self.meeting_step = 1
                # Collect all alive agents for voting
                self.meeting_queue = self.get_alive_agents().copy()
                self.meeting_timer = 0.0  # Reset timer for voting phase
        
        # Step 1: Voting Phase - all agents vote (all at once, or we could stagger)
        elif self.meeting_step == 1:
            # Process votes only once (check if queue is not empty to avoid reprocessing)
            if self.meeting_queue:
                votes = {}
                for agent in self.meeting_queue:
                    vote_target = agent.vote(self)
                    if vote_target:
                        votes[vote_target] = votes.get(vote_target, 0) + 1
                        print(f"{agent.id} votes for {vote_target}")
                    else:
                        print(f"{agent.id} skips vote")
                
                # Store votes for result phase
                if not votes:
                    print("No votes cast.")
                    self.meeting_votes = {}
                    self.meeting_result = None
                else:
                    # Find agent with most votes
                    max_votes = max(votes.values())
                    winners = [agent_id for agent_id, count in votes.items() if count == max_votes]
                    
                    if len(winners) == 1:
                        self.meeting_votes = votes
                        self.meeting_result = winners[0]
                        print(f"\nResult: {self.meeting_result} is voted out with {max_votes} vote(s)!")
                    else:
                        self.meeting_votes = votes
                        self.meeting_result = None
                        print(f"\nResult: Tie! No one is voted out.")
                
                self.meeting_queue = []  # Clear queue
                self.meeting_step = 2  # Move to result phase
                self.meeting_timer = 0.0
            # If queue is already empty, we're waiting for result phase timer (do nothing, just wait)
        
        # Step 2: Result Phase - execute ejection and update beliefs (after brief delay)
        elif self.meeting_step == 2:
            # Wait a moment to show the result, then process
            if self.meeting_timer >= 1.0:  # 1 second delay to show result
                # Handle result (whether someone was voted out or tie)
                if self.meeting_result:
                    voted_out_id = self.meeting_result
                    voted_agent = self._get_agent_by_id(voted_out_id)
                    if voted_agent:
                        # Mark agent as dead
                        voted_agent.state = "dead"
                        game_ended = self.game_over()
                        
                        # Create vote_result event as public fact for all agents
                        all_agents_for_event = [a for a in self.get_all_agents() 
                                              if (a.state == "alive" or a.id == voted_out_id)]
                        location = (all_agents_for_event[0].location if all_agents_for_event 
                                   else voted_agent.location if voted_agent else "unknown")
                        
                        vote_result_event = Event(
                            action="vote_result",
                            actor=self.meeting_reporter_id,
                            location=location,
                            witnesses=[a.id for a in all_agents_for_event],
                            visibility="public"
                        )
                        vote_result_event.voted_out_id = voted_out_id
                        vote_result_event.game_ended = game_ended
                        vote_result_event.votes = self.meeting_votes
                        
                        # Process vote result as public event (all agents observe it as FACT)
                        for agent in all_agents_for_event:
                            memory_item = MemoryItem(vote_result_event, "observation")
                            agent.update_knowledge(memory_item)
                            agent.update_belief(memory_item, self)
                        
                        # Additional logic: if game not over and dead agents >= bad agents,
                        # eliminate worlds where all dead agents are bad
                        if not game_ended:
                            alive_agents = self.get_alive_agents()
                            dead_agents = [a for a in self.get_all_agents() if a.state == "dead"]
                            num_bad = sum(1 for a in alive_agents if a.role == "bad")
                            
                            if len(dead_agents) >= num_bad and num_bad > 0:
                                # Eliminate worlds where all dead agents are bad
                                for agent in alive_agents:
                                    if not agent.knowledge["worlds"]:
                                        continue
                                    
                                    worlds_to_keep = []
                                    for world_state in agent.knowledge["worlds"]:
                                        # Check if all dead agents are bad in this world
                                        all_dead_are_bad = all(
                                            world_state.get(dead_agent.id) == "bad" 
                                            for dead_agent in dead_agents
                                        )
                                        if not all_dead_are_bad:
                                            worlds_to_keep.append(world_state)
                                    
                                    if worlds_to_keep:
                                        agent.knowledge["worlds"] = worlds_to_keep
                # If tie or no result, just end meeting without ejecting anyone
                
                # Reset behavior for all agents (return from voting behavior)
                for agent in self.get_alive_agents():
                    agent.behavior = "idle"
                
                # Return agents to their original locations before meeting
                for agent in self.get_alive_agents():
                    original_location = self.original_locations.get(agent.id)
                    if original_location:
                        # Remove from meeting room
                        if agent.location and agent.location in self.rooms:
                            self.rooms[agent.location].remove_agent(agent)
                        # Return to original location
                        agent.location = original_location
                        if original_location in self.rooms:
                            self.rooms[original_location].add_agent(agent)
                
                # Return to playing phase
                self.phase = GamePhase.PHASE_PLAYING
                self.meeting_queue = []
                self.meeting_reporter_id = None
                self.meeting_votes = None
                self.meeting_result = None
                self.original_locations = {}  # Clear stored locations
                
                # Meeting time did not count towards simulation time (current_time was paused)
                # last_meeting_time was set at meeting start, so automatic meetings will
                # trigger 10 seconds of PLAYING time after this meeting ends
                print(f"\n=== MEETING ENDED ===\n")
                print(f"All agents returned to their original locations")
                print(f"All agents returned to their original locations")
    
    def conduct_vote(self, reporter_id):
        """
        Legacy method - now calls start_meeting for backward compatibility.
        This is called from Actions.report, but start_meeting will be used instead.
        """
        self.start_meeting(reporter_id)
    
    def _has_kill_opportunity(self, npc):
        """
        Check if a bad agent has an opportunity to kill.
        
        Args:
            npc: NPC instance (should be bad agent)
        
        Returns:
            (target_id, True) if opportunity exists, (None, False) otherwise
        """
        if npc.role != "bad":
            return None, False
        
        alive_agents = self.get_alive_agents()
        agents_at_location = [a for a in alive_agents 
                             if a.location == npc.location and a.id != npc.id]
        
        # If alone with exactly one target who is good, we can kill
        if len(agents_at_location) == 1:
            target = agents_at_location[0]
            if target.role == "good":
                return target.id, True
        
        return None, False
    
    def update_npcs(self, delta_time=0.1):
        """
        Update NPCs: time-based action system.
        NPCs decide and act based on time, not every turn.
        Bad agents check for kill opportunities more frequently (within 2 seconds).
        Automatically triggers meetings every 10 seconds.
        
        Note: Meeting time does NOT count towards simulation time (current_time).
        This prevents meetings from triggering immediately after each other.
        
        Args:
            delta_time: time elapsed since last update
        """
        # If in meeting phase, delegate to update_meeting (but don't advance simulation time)
        if self.phase == GamePhase.PHASE_MEETING:
            self.update_meeting(delta_time)
            return
        
        # Only advance simulation time when NOT in meeting phase
        self.current_time += delta_time
        
        # Check if it's time for an automatic meeting (every 10 seconds)
        time_since_last_meeting = self.current_time - self.last_meeting_time
        if time_since_last_meeting >= self.meeting_interval:
            # Pick a random alive agent to be the "reporter" for the automatic meeting
            alive_agents = self.get_alive_agents()
            if alive_agents:
                reporter = random.choice(alive_agents)
                print(f"\n[Automatic Meeting] Triggered by {reporter.id} (10 seconds elapsed)")
                self.start_meeting(reporter.id)
                return  # Meeting phase started, skip normal NPC updates this frame
        
        from actions import Actions
        
        for npc in self.npcs:
            if npc.state != "alive":
                continue
            
            # For bad agents: check for kill opportunities more aggressively (within 2 seconds)
            if npc.role == "bad":
                # Check if at least 2 seconds have passed since last action
                time_since_last_action = self.current_time - npc.last_action_time
                
                # Check for kill opportunity if at least 2 seconds have passed
                if time_since_last_action >= 2.0:
                    target_id, has_opportunity = self._has_kill_opportunity(npc)
                    if has_opportunity:
                        # Take kill action immediately
                        print(f"[NPC Action] {npc.id} ({npc.role}): kill {target_id} [URGENT - kill opportunity]")
                        event = Actions.apply(self, npc, "kill", target_id)
                        
                        if event:
                            if event.action == "kill":
                                print(f"  → Event: {event.action} by {event.actor} at {event.location} (visibility: {event.visibility})")
                                print(f"    Target killed!")
                        
                        # Record action time and schedule next check in 2 seconds
                        npc.last_action_time = self.current_time
                        npc.next_action_time = self.current_time + 2.0  # Check again in 2 seconds
                        continue
            
            # Check if it's time for this NPC to act (normal scheduled action)
            if self.current_time >= npc.next_action_time:
                decision = npc.decide_action(self)
                if decision:
                    if isinstance(decision, tuple):
                        action_name = decision[0]
                        args = decision[1:] if len(decision) > 1 else []
                        
                        # Print action for visibility (especially important for bad agents)
                        args_str = f" {args[0]}" if args and len(args) == 1 else f" {args}" if args else ""
                        print(f"[NPC Action] {npc.id} ({npc.role}): {action_name}{args_str}")
                        
                        # Use shared Actions library
                        event = Actions.apply(self, npc, action_name, *args)
                        
                        # Print event details
                        if event:
                            if event.action == "say" and event.statement:
                                print(f"  → Event: {event.action} by {event.actor} at {event.location} (visibility: {event.visibility})")
                                print(f"    Statement: {event.statement}")
                            else:
                                print(f"  → Event: {event.action} by {event.actor} at {event.location} (visibility: {event.visibility})")
                                if event.action == "kill":
                                    print(f"    Target killed!")
                    else:
                        # Legacy support: if decision is just a string, treat as action with no args
                        print(f"[NPC Action] {npc.id} ({npc.role}): {decision}")
                        Actions.apply(self, npc, decision)
                
                # Schedule next action (random delay between 2-8 seconds)
                npc.last_action_time = self.current_time
                npc.next_action_time = self.current_time + random.uniform(2.0, 8.0)
        
        # Check win/loss conditions
        self._check_game_over()
    
    def _check_game_over(self):
        """Check win/loss conditions and set result."""
        alive_agents = self.get_alive_agents()
        num_good = sum(1 for a in alive_agents if a.role == "good")
        num_bad = sum(1 for a in alive_agents if a.role == "bad")
        
        # Bad agent(s) win: all good agents eliminated OR num bad >= num good
        if num_good == 0 or (num_bad >= num_good and num_bad > 0):
            self.result = "Bad agent(s) win"
            return
        
        # Good agents win: bad agent eliminated
        if num_bad == 0:
            self.result = "Good agents win"
            return
    
    def game_over(self):
        """Check if game is over."""
        return self.result is not None
    
    def print_state(self):
        """Print current game state."""
        print(f"\n=== Turn {self.turn} (Time: {self.current_time:.1f}s) ===")
        if self.player is not None and isinstance(self.player, Player):
            print(f"Player ({self.player.role}) in {self.player.location}, state: {self.player.state}, behavior: {self.player.behavior}")
        for npc in self.npcs:
            if npc.state == "alive":
                next_action_in = max(0, npc.next_action_time - self.current_time)
                print(f"{npc.id} ({npc.role}) in {npc.location}, behavior: {npc.behavior}, next action in: {next_action_in:.1f}s")
            else:
                print(f"{npc.id} - DEAD")
        print()
