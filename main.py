from world import World
from actions import Actions

def main():
    """Main game loop following: init → player action → event → belief update → NPC decision → repeat"""
    world = World(num_npcs=4, seed=42)
    
    print("=== Among-Us-like Game ===")
    print("You are the bad agent. Try to eliminate NPCs without being caught!")
    print("Actions: enter, sabo, report, kill")
    print()
    
    while not world.game_over():
        world.print_state()
        
        # Player action - get input and convert to action tuple
        action_input = input("Action (enter/sabo/report/kill/idle/task): ").strip().lower()
        if not action_input:
            continue
        
        action_parts = action_input.split()
        action_name = action_parts[0]
        args = action_parts[1:] if len(action_parts) > 1 else []
        
        # Handle interactive input for actions that need it
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
            print(f"Event: {event.action} by {event.actor} at {event.location} (visibility: {event.visibility})")
        
        # Belief update happens automatically in create_event
        # Voting happens automatically if event was a report
        
        # Check game over after player action (e.g., if caught)
        if world.game_over():
            break
        
        # NPC decision (time-based, simulates passage of time)
        # Each "turn" represents some time passing
        world.update_npcs(delta_time=1.0)  # 1 second per turn
        
        world.turn += 1
    
    print(f"\nGame Over: {world.result}")
    print(f"Total turns: {world.turn}")

if __name__ == "__main__":
    main()
