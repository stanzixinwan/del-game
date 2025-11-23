import time
import random

class Agent:
    """Base agent class with Kripke model knowledge representation."""
    
    def __init__(self, id, role="good", location="Entrance"):
        """
        Initialize an agent.
        
        Args:
            id: unique identifier for the agent
            role: "good" or "bad"
            location: starting location/room
        """
        self.id = id
        self.state = "alive"  # "alive" or "dead"
        self.role = role
        self.location = location
        self.action = None  # current action being performed
        self.behavior = "idle"  # "idle" | "task" | "sabo" | "voting"
        # Kripke Model: Knowledge representation
        # Worlds will be initialized by World._initialize_all_worlds()
        self.knowledge = {
            "worlds": [],  # possible worlds (belief states) - initialized by World
            "memory": []   # sequence of events observed
        }
    
    def update_knowledge(self, event):
        """Add an event to the agent's memory."""
        self.knowledge["memory"].append(event)
    
    def update_belief(self, event, world):
        """
        Update belief based on observed event.
        Uses Kripke model to update possible worlds.
        Base implementation - can be overridden or not used by subclasses.
        """
        if not self.knowledge["worlds"]:
            # If no worlds initialized, don't update
            return
        
        if event.visibility == "public":
            # Public events are certain
            self._update_belief_certain(event, world)
        elif event.visibility == "witnessed" and self.id in event.witnesses:
            # This agent witnessed the event
            self._update_belief_certain(event, world)
        elif event.visibility == "witnessed":
            # Someone else witnessed it, but we might have indirect knowledge
            self._update_belief_uncertain(event, world)
        # Private events don't update beliefs (not observed)
    
    def _update_belief_certain(self, event, world):
        """Update belief when event is certain (public or witnessed by this agent)."""
        if event.action == "kill":
            # If we see a kill, the actor is definitely bad
            # Eliminate all worlds where actor is not bad
            worlds_to_keep = []
            for world_state in self.knowledge["worlds"]:
                if world_state.get(event.actor) == "bad":
                    worlds_to_keep.append(world_state)
            self.knowledge["worlds"] = worlds_to_keep
        elif event.action == "sabo":
            # Sabotage: DON'T eliminate worlds, only sus gets updated
            # (sus update happens in world.py when event is witnessed)
            # No world elimination for sabo
            pass
        elif event.action == "report":
            # Reports provide information but don't eliminate worlds
            pass
    
    def _update_belief_uncertain(self, event, world):
        """Update belief when event is uncertain (witnessed by others but not us)."""
        # For uncertain events, we might adjust beliefs but don't eliminate worlds
        # This could be expanded later for more sophisticated reasoning
        pass
    
    def get_any_world(self):
        """Get any world state (for compatibility)."""
        if not self.knowledge["worlds"]:
            return None
        return self.knowledge["worlds"][0]
    
    def vote(self, world):
        """
        Vote based on any world.
        Returns the id of the agent to vote for (or None to skip).
        Base implementation - overridden by NPC for good agents.
        """
        any_world = self.get_any_world()
        if not any_world:
            return None
        
        # Find the agent marked as "bad" in the world
        for agent_id, role in any_world.items():
            if role == "bad":
                agent = world._get_agent_by_id(agent_id)
                if agent and agent.state == "alive":
                    return agent_id
        
        return None
    
    def get_agents_at_location(self, world, location):
        """Get all agents (alive) at a given location."""
        agents = []
        if hasattr(world, 'player') and world.player.location == location and world.player.state == "alive":
            agents.append(world.player)
        if hasattr(world, 'npcs'):
            agents.extend([npc for npc in world.npcs if npc.location == location and npc.state == "alive"])
        return agents


class Player(Agent):
    """Player agent (typically the bad role)."""
    
    def __init__(self, id="player", role="bad", location="Entrance"):
        super().__init__(id, role, location)
        # Player inherits worlds initialization from base class with own role
    
    def vote(self, world):
        """
        Interactive voting for player.
        Returns the id of the agent to vote for (or None to skip).
        """
        alive_agents = world.get_alive_agents()
        # Filter out self
        candidates = [a for a in alive_agents if a.id != self.id]
        
        if not candidates:
            print("No one to vote for!")
            return None
        
        print("\n=== YOUR VOTE ===")
        print("Available candidates:")
        for i, agent in enumerate(candidates):
            print(f"  {i}: {agent.id} ({agent.role})")
        print(f"  {len(candidates)}: Skip vote")
        
        try:
            choice = input(f"Vote (0-{len(candidates)}): ").strip()
            if not choice:
                return None
            
            choice_num = int(choice)
            if choice_num == len(candidates):
                # Skip vote
                return None
            elif 0 <= choice_num < len(candidates):
                return candidates[choice_num].id
            else:
                print("Invalid choice, skipping vote.")
                return None
        except (ValueError, IndexError):
            print("Invalid input, skipping vote.")
            return None


class NPC(Agent):
    """NPC agent (typically good role, can observe and make decisions)."""
    
    def __init__(self, id, role="good", location="Entrance"):
        super().__init__(id, role, location)
        # Sus tracking: suspicion level for each agent (initially 0)
        self.sus = {}  # Will be initialized by World with all agent ids
        # Time-based action system
        self.next_action_time = 0.0  # When this NPC should decide on next action
        self.action_duration = 0.0  # How long current action takes
    
    def update_sus(self, agent_id, delta):
        """Update suspicion for an agent."""
        if agent_id in self.sus:
            self.sus[agent_id] += delta
            self.sus[agent_id] = max(0, self.sus[agent_id])  # Keep non-negative
    
    def vote(self, world):
        """
        Good agents vote: for every other id, count worlds where id_role=bad.
        Vote for the one with the largest count.
        If tie, use sus values.
        """
        if self.role != "good":
            return super().vote(world)  # Fallback to base implementation
        
        # Count worlds where each agent is bad
        agent_scores = {}
        all_agents = world.get_all_agents()
        
        for agent in all_agents:
            if agent.id == self.id or agent.state != "alive":
                continue
            
            # Count worlds where this agent is bad
            count = 0
            for world_state in self.knowledge["worlds"]:
                if world_state.get(agent.id) == "bad":
                    count += 1
            
            agent_scores[agent.id] = count
        
        if not agent_scores:
            return None
        
        # Debug output
        print(f"  {self.id} world counts: {agent_scores}, sus: {self.sus}")
        
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
                sus_values = [self.sus.get(cid, 0) for cid in candidates]
                for candidate_id in candidates:
                    sus_value = self.sus.get(candidate_id, 0)
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
    
    def decide_action(self, world):
        """
        NPC decision making - delegates to npc_policy.
        Returns action tuple or None.
        """
        from npc_policy import choose_action
        return choose_action(self, world)
