from agent import Agent, NPC, Player
from event import Event
import time
import random

class World:
    """World representation with id_roles."""
    
    def __init__(self, num_npcs=4, seed=None, rooms=["A", "B", "C", "D"], player=None, npcs=None):
        """
        Initialize the game world.
        
        Args:
            num_npcs: number of NPC agents (used only if npcs is None)
            seed: random seed for reproducibility
            rooms: list of room names (default: ["Entrance", "Engine", "Storage", "Medbay", "Admin"])
            player: Player instance (default: creates new Player with role="bad")
            npcs: list of NPC instances (default: creates num_npcs NPCs with role="good")
        """
        if seed is not None:
            random.seed(seed)
        
        # Set rooms
        self.rooms = rooms
        
        # Set player
        if player is not None:
            self.player = player
        else:
            self.player = Player("player", role="bad", location=self.rooms[0] if self.rooms else "Storage")
        
        # Set NPCs
        if npcs is not None:
            self.npcs = npcs
        else:
            # Create NPCs with random locations from available rooms
            self.npcs = [NPC(f"npc{i}", role="good", location=random.choice(self.rooms)) for i in range(num_npcs)]
        
        self.result = None
        self.turn = 0
        self.current_time = 0.0  # Current game time
        self.event_history = []  # Global event history
        
        # Initialize all possible worlds and sus for all agents
        self._initialize_all_worlds()
        self._initialize_sus()
        self._initialize_npc_times()
    
    def _initialize_all_worlds(self):
        """Initialize all possible worlds for each agent (all cases of 1 bad agent)."""
        all_agents = self.get_all_agents()
        all_agent_ids = [a.id for a in all_agents]
        
        # Create all possible worlds (one bad agent, rest good)
        for agent in all_agents:
            worlds = []
            for bad_agent_id in all_agent_ids:
                # Create a world where this agent_id is bad
                world_state = {}
                for aid in all_agent_ids:
                    if aid == bad_agent_id:
                        world_state[aid] = "bad"
                    else:
                        world_state[aid] = "good"
                # Eliminate world where agent's own role is wrong
                if world_state.get(agent.id) == agent.role:
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
        return [self.player] + self.npcs
    
    def get_alive_agents(self):
        """Get all alive agents."""
        return [a for a in self.get_all_agents() if a.state == "alive"]
    
    def create_event(self, action, actor, location, witnesses=None, visibility="private"):
        """
        Create and process an event.
        
        Args:
            action: action type
            actor: agent id performing action
            location: location of event
            witnesses: list of witness ids (None for private)
            visibility: "private" | "witnessed" | "public"
        
        Returns:
            Event object
        """
        event = Event(action, actor, location, witnesses, visibility)
        self.event_history.append(event)
        
        # Update knowledge based on visibility
        if visibility == "private":
            # Only the actor knows
            actor_agent = self._get_agent_by_id(actor)
            if actor_agent:
                actor_agent.update_knowledge(event)
        elif visibility == "witnessed":
            # Actor and witnesses know
            actor_agent = self._get_agent_by_id(actor)
            if actor_agent:
                actor_agent.update_knowledge(event)
            if witnesses:
                for witness_id in witnesses:
                    witness_agent = self._get_agent_by_id(witness_id)
                    if witness_agent:
                        witness_agent.update_knowledge(event)
                        witness_agent.update_belief(event, self)
                        # Update sus for NPCs when witnessing events like sabo (no world elimination)
                        if isinstance(witness_agent, NPC) and event.action == "sabo":
                            witness_agent.update_sus(event.actor, 0.2)  # Increase suspicion
        elif visibility == "public":
            # All agents know
            for agent in self.get_alive_agents():
                agent.update_knowledge(event)
                agent.update_belief(event, self)
                # Update sus for NPCs when witnessing events like sabo (no world elimination)
                if isinstance(agent, NPC) and event.action == "sabo":
                    agent.update_sus(event.actor, 0.2)  # Increase suspicion
        
        return event
    
    def _get_agent_by_id(self, agent_id):
        """Get agent by id."""
        if agent_id == self.player.id:
            return self.player
        for npc in self.npcs:
            if npc.id == agent_id:
                return npc
        return None
    
    def get_agents_at_location(self, location):
        """Get all alive agents at a given location."""
        return [a for a in self.get_alive_agents() if a.location == location]
    
    def conduct_vote(self, reporter_id):
        """
        Conduct a vote after a report.
        Everyone votes based on their most believed world.
        Returns the agent id with most votes, or None if tie/no votes.
        Also updates beliefs based on voting results.
        """
        votes = {}
        alive_agents = self.get_alive_agents()
        
        print(f"\n=== VOTING (Reported by {reporter_id}) ===")
        
        for agent in alive_agents:
            vote_target = agent.vote(self)
            if vote_target:
                votes[vote_target] = votes.get(vote_target, 0) + 1
                print(f"{agent.id} votes for {vote_target}")
            else:
                print(f"{agent.id} skips vote")
        
        if not votes:
            print("No votes cast.")
            return None
        
        # Find agent with most votes
        max_votes = max(votes.values())
        winners = [agent_id for agent_id, count in votes.items() if count == max_votes]
        
        if len(winners) == 1:
            voted_out_id = winners[0]
            print(f"\nResult: {voted_out_id} is voted out with {max_votes} vote(s)!")
            
            # Update beliefs based on voting
            self._update_beliefs_after_vote(voted_out_id, votes)
            
            return voted_out_id
        else:
            print(f"\nResult: Tie! No one is voted out.")
            return None
    
    def _update_beliefs_after_vote(self, voted_out_id, votes):
        """
        Update beliefs after voting:
        1. If game not over and dead npc number >= bad agent number, eliminate worlds where all dead agents are bad
        2. If I know my role is good and get voted by agent n, eliminate worlds where voter is good
        """
        voted_agent = self._get_agent_by_id(voted_out_id)
        if not voted_agent:
            return
        
        # Mark agent as dead
        voted_agent.state = "dead"
        
        # Check if we should eliminate worlds (dead npc number >= bad agent number)
        alive_agents = self.get_alive_agents()
        dead_npcs = [npc for npc in self.npcs if npc.state == "dead"]
        num_bad = sum(1 for a in alive_agents if a.role == "bad")
        
        if len(dead_npcs) >= num_bad and num_bad > 0:
            # Eliminate worlds where all dead agents are bad
            for agent in self.get_alive_agents():
                if not agent.knowledge["worlds"]:
                    continue
                
                worlds_to_keep = []
                for world_state in agent.knowledge["worlds"]:
                    # Check if all dead NPCs are bad in this world
                    all_dead_are_bad = all(
                        world_state.get(dead_npc.id) == "bad" 
                        for dead_npc in dead_npcs
                    )
                    if not all_dead_are_bad:
                        worlds_to_keep.append(world_state)
                
                if worlds_to_keep:
                    agent.knowledge["worlds"] = worlds_to_keep
        
        # If I know my role is good and get voted by agent n, eliminate worlds where voter is good
        if voted_agent.role == "good":
            # The voted-out agent knows they're good, so voters might be bad
            for voter_id, vote_count in votes.items():
                if vote_count > 0:
                    voter = self._get_agent_by_id(voter_id)
                    if voter and voter.state == "alive":
                        # Update beliefs: eliminate worlds where voter is good
                        if voted_agent.knowledge["worlds"]:
                            worlds_to_keep = []
                            for world_state in voted_agent.knowledge["worlds"]:
                                if world_state.get(voter_id) != "good":
                                    worlds_to_keep.append(world_state)
                            if worlds_to_keep:
                                voted_agent.knowledge["worlds"] = worlds_to_keep
    
    def update_npcs(self, delta_time=0.1):
        """
        Update NPCs: time-based action system.
        NPCs decide and act based on time, not every turn.
        
        Args:
            delta_time: time elapsed since last update
        """
        from actions import Actions
        
        self.current_time += delta_time
        
        for npc in self.npcs:
            if npc.state != "alive":
                continue
            
            # Check if it's time for this NPC to act
            if self.current_time >= npc.next_action_time:
                decision = npc.decide_action(self)
                if decision:
                    if isinstance(decision, tuple):
                        action_name = decision[0]
                        args = decision[1:] if len(decision) > 1 else []
                        # Use shared Actions library
                        Actions.apply(self, npc, action_name, *args)
                    else:
                        # Legacy support: if decision is just a string, treat as action with no args
                        Actions.apply(self, npc, decision)
                
                # Schedule next action (random delay between 2-8 seconds)
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
        print(f"Player ({self.player.role}) in {self.player.location}, state: {self.player.state}, behavior: {self.player.behavior}")
        for npc in self.npcs:
            if npc.state == "alive":
                any_world = npc.get_any_world()
                next_action_in = max(0, npc.next_action_time - self.current_time)
                if any_world:
                    print(f"{npc.id} ({npc.role}) in {npc.location}, behavior: {npc.behavior}, next action in: {next_action_in:.1f}s")
                    print(f"  Worlds: {len(npc.knowledge['worlds'])}, Example: {any_world}")
                    print(f"  Sus: {npc.sus}")
                else:
                    print(f"{npc.id} ({npc.role}) in {npc.location}, behavior: {npc.behavior}, next action in: {next_action_in:.1f}s")
                    print(f"  Worlds: 0")
                    print(f"  Sus: {npc.sus}")
            else:
                print(f"{npc.id} - DEAD")
        print()
