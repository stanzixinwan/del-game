from world import World
from actions import Actions
from agent import NPC
import random
import time

def main():
    """Main game loop - supports both player mode and simulation mode."""
    print("=== Game Mode Selection ===")
    print("1. Player mode (you play as bad agent)")
    print("2. Simulation mode (all NPCs, no player)")
    
    mode_choice = input("Choose mode (1 or 2): ").strip()
    
    if mode_choice == "2":
        simulate_all_npcs()
    else:
        player_mode()

def player_mode():
    """Main game loop with player interaction."""
    world = World(num_npcs=4, seed=42)
    
    print("\n=== Game Start ===")
    print("You are the bad agent. Try to eliminate NPCs without being caught!")
    print("Instant Actions (produce events): enter, sabo, report, kill, say")
    print("  say format: say <predicate> <subject> <value>")
    print("    predicate: role | location | did")
    print("    subject: agent_id")
    print("    value: the claim (e.g., 'bad', 'Engine', 'task')")
    print("Behavior States (no events): idle, task, voting")
    print()
    
    while not world.game_over():
        world.print_state()
        
        # Player action - get input and convert to action tuple
        action_input = input("Action (enter/sabo/report/kill/say/idle/task): ").strip().lower()
        if not action_input:
            continue
        
        action_parts = action_input.split()
        action_name = action_parts[0]
        args = action_parts[1:] if len(action_parts) > 1 else []
        
        # Handle interactive input for actions that need it
        # Special handling for "say" action: convert numeric subject index to agent ID
        if action_name == "say" and len(args) >= 2:
            # If subject (args[1]) is a numeric string, convert it to agent ID
            try:
                subject_index = int(args[1])
                alive_agents = world.get_alive_agents()
                if 0 <= subject_index < len(alive_agents):
                    args[1] = alive_agents[subject_index].id
            except (ValueError, IndexError):
                # Not a numeric index or out of range, treat as agent ID directly
                pass
        
        if action_name == "enter" and not args:
            print(f"Available rooms: {', '.join(world.rooms)}")
            target_room = input("Go to: ").strip()
            args = [target_room] if target_room else []
        elif action_name == "sabo" and not args:
            sabo_type = input("Sabotage type: ").strip()
            args = [sabo_type] if sabo_type else []
        elif action_name == "report" and not args:
            info = input("Report info: ").strip()
            args = [info] if info else []
        elif action_name == "say" and len(args) < 3:
            # SAY requires: predicate, subject, value
            # predicate: "role" | "location" | "did"
            print("Say action requires: predicate subject value")
            print("  predicate: role | location | did")
            print("  subject: agent_id")
            print("  value: the claim (e.g., 'bad', 'Engine', 'task')")
            
            if len(args) == 0:
                predicate = input("Predicate (role/location/did): ").strip().lower()
                if predicate not in ["role", "location", "did"]:
                    print(f"Invalid predicate: {predicate}. Must be 'role', 'location', or 'did'")
                    continue
                args.append(predicate)
            
            if len(args) == 1:
                # Show available agents
                alive_agents = world.get_alive_agents()
                print("Available agents:")
                for i, agent in enumerate(alive_agents):
                    print(f"  {i}: {agent.id}")
                try:
                    choice = int(input("Subject (agent number): "))
                    subject_id = alive_agents[choice].id
                    args.append(subject_id)
                except (ValueError, IndexError):
                    print("Invalid choice!")
                    continue
            
            if len(args) == 2:
                value = input("Value: ").strip()
                if value:
                    args.append(value)
                else:
                    print("Value cannot be empty!")
                    continue
        elif action_name == "kill" and not args:
            # Show available targets
            targets = [a for a in world.get_agents_at_location(world.player.location) 
                      if a.id != world.player.id and a.state == "alive"]
            if not targets:
                print("No targets at this location!")
                continue
            print("Available targets:")
            for i, target in enumerate(targets):
                print(f"  {i}: {target.id}")
            try:
                choice = int(input("Target (number): "))
                target_id = targets[choice].id
                args = [target_id]
            except (ValueError, IndexError):
                print("Invalid choice!")
                continue
        
        # Apply action using shared Actions library
        event = Actions.apply(world, world.player, action_name, *args)
        
        if event:
            if event.action == "say" and event.statement:
                print(f"Event: {event.action} by {event.actor} at {event.location} (visibility: {event.visibility})")
                print(f"  Statement: {event.statement}")
            else:
                print(f"Event: {event.action} by {event.actor} at {event.location} (visibility: {event.visibility})")
        
        # Belief update happens automatically in create_event
        # If report was made, voting will happen automatically in Actions.report
        # Player can make statements during voting (handled in world.conduct_vote)
        
        # Check game over after player action (e.g., if caught)
        if world.game_over():
            break
        
        # NPC decision (time-based, simulates passage of time)
        # Each "turn" represents some time passing
        world.update_npcs(delta_time=1.0)  # 1 second per turn
        
        world.turn += 1
    
    print(f"\nGame Over: {world.result}")
    print(f"Total turns: {world.turn}")


def simulate_all_npcs():
    """Simulation mode: all agents are NPCs, no player input."""
    import random
    
    # Create NPCs: one bad, rest good
    num_npcs = 5
    rooms = ["A", "B", "C", "D"]
    npcs = []
    
    # Create one bad NPC and rest good
    for i in range(num_npcs):
        role = "bad" if i == 0 else "good"  # First NPC is bad
        npcs.append(NPC(f"npc{i}", role=role, location=random.choice(rooms)))
    
    # Create world with no player (all NPCs)
    world = World(num_npcs=0, seed=42, rooms=rooms, player=False, npcs=npcs)
    
    print("\n=== Simulation Mode ===")
    print(f"Running simulation with {num_npcs} NPCs (1 bad, {num_npcs-1} good)")
    print("All agents will act autonomously.")
    print()
    
    max_turns = 50  # Limit simulation to prevent infinite loops
    turn_delay = 0.5  # Small delay between turns for readability
    
    while not world.game_over() and world.turn < max_turns:
        world.print_state()
        
        # All NPCs act in this turn (time-based system)
        world.update_npcs(delta_time=1.0)  # 1 second per turn
        
        # Small delay for readability
        time.sleep(turn_delay)
        
        world.turn += 1
        
        # Check if we should continue
        if world.game_over():
            break
    
    print(f"\n=== Simulation Complete ===")
    print(f"Result: {world.result}")
    print(f"Total turns: {world.turn}")
    
    # Print final state
    print("\n=== Final State ===")
    alive_agents = world.get_alive_agents()
    for agent in alive_agents:
        print(f"{agent.id} ({agent.role}) - {agent.state} in {agent.location}")


if __name__ == "__main__":
    main()
