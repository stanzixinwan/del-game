import time
import random
from memory import Certainty

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
            "memory": []   # sequence of MemoryItems observed
        }
    
    def update_knowledge(self, memory_item):
        """
        Add a MemoryItem to the agent's memory.
        
        Args:
            memory_item: MemoryItem instance to add to memory
        """
        self.knowledge["memory"].append(memory_item)
    
    def update_belief(self, memory_item, world_context):
        """
        DEL Update Cycle: Update belief based on MemoryItem.
        
        Rigorously distinguishes between:
        - Hard Knowledge (FACT, S5): Eliminates worlds
        - Soft Belief (UNCERTAIN, KD45): Updates suspicion scores
        
        Args:
            memory_item: MemoryItem instance wrapping an Event
            world_context: World instance for context (needed for game state checks)
        """
        if not self.knowledge["worlds"]:
            # If no worlds initialized, don't update
            return
        
        event = memory_item.event
        
        # Branch based on certainty level
        if memory_item.certainty == Certainty.FACT:
            # Hard Knowledge: Perform World Elimination Update
            self._update_belief_hard_knowledge(memory_item, world_context)
        elif memory_item.certainty == Certainty.UNCERTAIN:
            # Soft Belief: Update suspicion scores
            self._update_belief_soft_belief(memory_item, world_context)
        # VERIFIED and DISPROVED can be handled later if needed
    
    def _update_belief_hard_knowledge(self, memory_item, world_context):
        """
        Hard Knowledge (FACT) branch: Eliminate inconsistent worlds.
        S5 Knowledge: If I know it, it must be true in all possible worlds.
        """
        event = memory_item.event
        
        if event.action == "kill":
            # KILL (observed): Fact. Actor must be "bad".
            # Eliminate all worlds where actor is "good"
            if not self.knowledge["worlds"]:
                return
            
            worlds_to_keep = []
            for world_state in self.knowledge["worlds"]:
                if world_state.get(event.actor) == "bad":
                    worlds_to_keep.append(world_state)
            self.knowledge["worlds"] = worlds_to_keep
            
        elif event.action == "enter":
            # ENTER/VISIT (observed): Fact. Actor is at Location.
            # Optional: Could track location history for future reasoning
            # For now, this is informational only (no world elimination)
            pass
            
        elif event.action == "vote_result":
            # VOTE_RESULT (public): Fact.
            voted_out_id = getattr(event, 'voted_out_id', None)
            game_ended = getattr(event, 'game_ended', False)
            votes = getattr(event, 'votes', {})
            
            if not voted_out_id:
                return
            
            # If I was voted out and I know I'm good, eliminate worlds where voters are good
            # (since good agents wouldn't vote out another good agent without strong reason)
            if voted_out_id == self.id and self.role == "good":
                # I know I'm good, so voters might be bad
                if not self.knowledge["worlds"]:
                    return
                
                # Start with current worlds and filter progressively for each voter
                worlds_to_keep = list(self.knowledge["worlds"])
                
                for voter_id, vote_count in votes.items():
                    if vote_count > 0:
                        voter = world_context._get_agent_by_id(voter_id)
                        if voter and voter.state == "alive":
                            # Eliminate worlds where this voter is good
                            # Filter from the current worlds_to_keep (progressive filtering)
                            filtered_worlds = []
                            for world_state in worlds_to_keep:
                                if world_state.get(voter_id) != "good":
                                    filtered_worlds.append(world_state)
                            worlds_to_keep = filtered_worlds
                            
                            # If no worlds remain, stop filtering
                            if not worlds_to_keep:
                                break
                
                # Update worlds once after processing all voters
                if worlds_to_keep:
                    self.knowledge["worlds"] = worlds_to_keep
            
            # If X was voted out and game didn't end (and we know there's only 1 bad agent),
            # then X must have been "good". Eliminate worlds where X is "bad".
            elif not game_ended:
                # If game continues after vote, voted agent was likely good
                # Eliminate worlds where voted agent is bad
                if not self.knowledge["worlds"]:
                    return
                
                worlds_to_keep = []
                for world_state in self.knowledge["worlds"]:
                    if world_state.get(voted_out_id) == "good":
                        worlds_to_keep.append(world_state)
                
                if worlds_to_keep:
                    self.knowledge["worlds"] = worlds_to_keep
        
        # SABO and REPORT don't eliminate worlds directly
        # (SABO updates sus, REPORT triggers voting)
    
    def _update_belief_soft_belief(self, memory_item, world_context):
        """
        Soft Belief (UNCERTAIN) branch: Update suspicion scores.
        KD45 Belief: Adjust belief weights without eliminating worlds.
        """
        event = memory_item.event
        
        if event.action == "say" and event.statement:
            # SAY (heard): Uncertain. Process statement content.
            statement = event.statement
            
            # Only NPCs have sus tracking
            if not hasattr(self, 'sus'):
                return
            
            # If predicate is "role" and value is "bad", increase target's sus
            if statement.predicate == "role" and statement.value == "bad":
                target_id = statement.subject
                speaker_id = statement.speaker
                
                # Slightly increase suspicion of the target
                # Trust in speaker could be considered (future enhancement)
                if target_id in self.sus and target_id != self.id:
                    # Small sus increase for hearsay accusations
                    self.update_sus(target_id, 0.1)
        
        elif event.action == "sabo":
            # SABO (heard about): Increase suspicion of actor
            if hasattr(self, 'sus'):
                actor_id = event.actor
                if actor_id in self.sus and actor_id != self.id:
                    self.update_sus(actor_id, 0.2)
    
    def update_sus(self, agent_id, delta):
        """
        Update suspicion for an agent.
        Base implementation - does nothing for base Agent class.
        Overridden in NPC class.
        """
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
        self.last_action_time = 0.0  # When this NPC last performed an action
    
    def update_sus(self, agent_id, delta):
        """Update suspicion for an agent."""
        if hasattr(self, 'sus') and agent_id in self.sus:
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
