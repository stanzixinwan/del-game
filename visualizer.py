"""
PyGame Visualizer for DEL-Game

Visualizes the game state and agent cognitive states (Kripke worlds, suspicion, memory).
Click agents to view their DEL/Kripke model internal states.
"""

import pygame
import sys
# Import core game modules
from world import World
from agent import Player, NPC

# Initialize PyGame
pygame.init()

# Screen constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Color definitions (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
BLUE = (50, 50, 200)
GREEN = (50, 200, 50)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
DARK_BG = (30, 30, 30)
DEAD_COLOR = (128, 128, 128)  # Gray for dead agents/corpses

# Create screen and clock
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("DEL Logic Visualizer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 14)

# Global variables
game_world = None
ROOM_COORDS = {}
agent_positions = {}
is_player_mode = False  # Whether we're in player mode or simulation mode


def generate_room_coords(rooms):
    """
    Generate screen coordinates for rooms in a grid layout.
    
    Args:
        rooms: List of room names (e.g., ["A", "B", "C", "D"])
    
    Returns:
        Dictionary mapping room names to (x, y) coordinates
    """
    coords = {}
    num_rooms = len(rooms)
    
    # Calculate grid dimensions (2 columns)
    cols = 2
    rows = (num_rooms + cols - 1) // cols  # Ceiling division
    
    # Room spacing
    start_x, start_y = 150, 150
    spacing_x, spacing_y = 300, 200
    
    for i, room in enumerate(rooms):
        row = i // cols
        col = i % cols
        x = start_x + col * spacing_x
        y = start_y + row * spacing_y
        coords[room] = (x, y)
    
    # Add coordinate for removed corpses (None location)
    coords[None] = (50, 50)
    
    return coords


def draw_room_connections():
    """Draw connection lines between connected rooms."""
    if not game_world or not hasattr(game_world, 'connections'):
        return
    
    # Draw connections (lines between connected rooms)
    drawn_connections = set()  # Track to avoid drawing duplicates
    for room1, connected_rooms in game_world.connections.items():
        if room1 not in ROOM_COORDS:
            continue
        x1, y1 = ROOM_COORDS[room1]
        for room2 in connected_rooms:
            if room2 not in ROOM_COORDS:
                continue
            # Avoid drawing the same connection twice
            connection_pair = tuple(sorted([room1, room2]))
            if connection_pair in drawn_connections:
                continue
            drawn_connections.add(connection_pair)
            
            x2, y2 = ROOM_COORDS[room2]
            # Draw connection line (lighter gray)
            pygame.draw.line(screen, (60, 60, 60), (x1, y1), (x2, y2), 2)


def draw_rooms():
    """Draw room circles on the map."""
    for room_name, (x, y) in ROOM_COORDS.items():
        if room_name:  # Skip None (cemetery)
            # Draw room circle
            pygame.draw.circle(screen, GRAY, (x, y), 40)
            # Draw room name
            text = font.render(room_name, True, WHITE)
            text_rect = text.get_rect(center=(x, y))
            screen.blit(text, (text_rect.x, y + 50))


def draw_dead_agents():
    """Draw dead agents as gray circles at their death location."""
    global agent_positions
    
    all_agents = game_world.get_all_agents()
    dead_agents = [a for a in all_agents if a.state == "dead" and a.location is not None]
    
    for i, agent in enumerate(dead_agents):
        if agent.location in ROOM_COORDS:
            base_x, base_y = ROOM_COORDS[agent.location]
            # Offset to avoid overlap with alive agents
            offset_x = -20 + (i % 3) * 15
            offset_y = -20 + (i // 3) * 15
            
            pos_x = base_x + offset_x
            pos_y = base_y + offset_y
            
            # Store position for click detection
            agent_positions[agent.id] = (pos_x, pos_y)
            
            # Draw dead agent (gray, smaller)
            pygame.draw.circle(screen, DEAD_COLOR, (pos_x, pos_y), 12)
            pygame.draw.circle(screen, BLACK, (pos_x, pos_y), 12, 2)  # Border
            
            # Draw ID
            id_text = small_font.render(agent.id, True, WHITE)
            screen.blit(id_text, (pos_x - 15, pos_y - 25))


def draw_alive_agents():
    """Draw alive agents with color coding (red=player, blue=NPC)."""
    global agent_positions
    
    alive_agents = game_world.get_alive_agents()
    
    for i, agent in enumerate(alive_agents):
        if agent.location and agent.location in ROOM_COORDS:
            base_x, base_y = ROOM_COORDS[agent.location]
            
            # Offset to avoid overlap
            agents_in_room = [a for a in alive_agents if a.location == agent.location]
            room_index = agents_in_room.index(agent)
            offset_x = -20 + (room_index % 3) * 20
            offset_y = -20 + (room_index // 3) * 20
            
            pos_x = base_x + offset_x
            pos_y = base_y + offset_y
            
            # Store position for click detection
            agent_positions[agent.id] = (pos_x, pos_y)
            
            # Color coding: Player = RED, Bad NPC = Dark Red, Good NPC = BLUE
            if isinstance(agent, Player):
                color = RED
                # Add border for player
                pygame.draw.circle(screen, (255, 255, 255), (pos_x, pos_y), 17, 2)
            elif agent.role == "bad":
                color = (150, 0, 0)  # Dark red for bad NPCs
                # Add pulsing border for bad agents to make them more visible
                pygame.draw.circle(screen, (255, 100, 100), (pos_x, pos_y), 17, 2)
            else:
                color = BLUE
            
            # Draw agent circle
            pygame.draw.circle(screen, color, (pos_x, pos_y), 15)
            
            # Draw ID above agent
            id_text = font.render(agent.id, True, WHITE)
            screen.blit(id_text, (pos_x - 15, pos_y - 30))
            
            # Draw role indicator (small badge)
            role_text = small_font.render(agent.role[0].upper(), True, WHITE)
            role_bg = RED if agent.role == "bad" else GREEN
            pygame.draw.circle(screen, role_bg, (pos_x + 10, pos_y - 10), 8)
            screen.blit(role_text, (pos_x + 6, pos_y - 13))
            
            # Draw current action/behavior indicator (if not idle)
            if agent.action:
                # Color code actions: kill=red, sabo=orange, enter=blue, etc.
                if agent.action == "kill":
                    action_color = RED
                elif agent.action == "sabo":
                    action_color = (255, 165, 0)  # Orange
                elif agent.action == "enter":
                    action_color = BLUE
                elif agent.action == "report":
                    action_color = GREEN
                else:
                    action_color = (255, 255, 0)  # Yellow for other actions
                action_text = small_font.render(agent.action.upper(), True, action_color)
                screen.blit(action_text, (pos_x - 25, pos_y + 18))
            elif agent.behavior and agent.behavior != "idle":
                behavior_text = small_font.render(agent.behavior.upper(), True, (200, 200, 255))
                screen.blit(behavior_text, (pos_x - 20, pos_y + 18))


def draw_meeting_banner():
    """Draw meeting banner at the top of the screen when in meeting phase."""
    if not game_world or not hasattr(game_world, 'phase'):
        return
    
    from world import GamePhase
    if game_world.phase == GamePhase.PHASE_MEETING:
        # Draw banner background
        banner_height = 50
        banner_rect = pygame.Rect(0, 0, SCREEN_WIDTH, banner_height)
        pygame.draw.rect(screen, (100, 50, 50), banner_rect)  # Dark red background
        pygame.draw.rect(screen, (255, 200, 0), banner_rect, 3)  # Yellow border
        
        # Draw banner text
        banner_text = font.render("=== MEETING IN PROGRESS ===", True, (255, 255, 0))
        text_rect = banner_text.get_rect(center=(SCREEN_WIDTH // 2, banner_height // 2))
        screen.blit(banner_text, text_rect)
        
        # Show meeting step info
        if hasattr(game_world, 'meeting_step'):
            step_names = ["Statements", "Voting", "Results"]
            step_name = step_names[game_world.meeting_step] if game_world.meeting_step < len(step_names) else "Unknown"
            step_text = small_font.render(f"Step: {step_name}", True, WHITE)
            screen.blit(step_text, (SCREEN_WIDTH - 150, 15))
        
        # Show reporter if available
        if hasattr(game_world, 'meeting_reporter_id') and game_world.meeting_reporter_id:
            reporter_text = small_font.render(f"Reported by: {game_world.meeting_reporter_id}", True, WHITE)
            screen.blit(reporter_text, (20, 30))


def draw_game_info():
    """Draw game state info in top-left corner."""
    info_y = 10
    turn_text = font.render(f"Turn: {game_world.turn}", True, WHITE)
    screen.blit(turn_text, (10, info_y))
    
    info_y += 25
    time_text = font.render(f"Time: {game_world.current_time:.1f}s", True, WHITE)
    screen.blit(time_text, (10, info_y))
    
    if game_world.result:
        info_y += 25
        result_text = font.render(f"Game Over: {game_world.result}", True, RED)
        screen.blit(result_text, (10, info_y))
    
    # Show mode
    info_y += 25
    mode_text = font.render(f"Mode: {'Player' if is_player_mode else 'Simulation'}", True, WHITE)
    screen.blit(mode_text, (10, info_y))
    
    # Show phase (if in meeting)
    if hasattr(game_world, 'phase'):
        from world import GamePhase
        if game_world.phase == GamePhase.PHASE_MEETING:
            info_y += 25
            phase_text = font.render(f"Phase: MEETING", True, (255, 255, 0))  # Yellow
            screen.blit(phase_text, (10, info_y))
        else:
            # Show time until next automatic meeting
            if hasattr(game_world, 'last_meeting_time') and hasattr(game_world, 'meeting_interval'):
                time_since_last = game_world.current_time - game_world.last_meeting_time
                time_until_next = max(0, game_world.meeting_interval - time_since_last)
                info_y += 25
                next_meeting_text = font.render(f"Next meeting in: {time_until_next:.1f}s", True, (200, 200, 255))
                screen.blit(next_meeting_text, (10, info_y))


def draw_player_controls():
    """Draw player controls/help panel in bottom-left (above event log)."""
    if not is_player_mode or not game_world or not game_world.player:
        return
    
    controls = [
        "Controls:",
        "E - Enter (move to room)",
        "K - Kill target",
        "S - Say statement",
        "R - Report",
        "B - Sabotage",
        "I - Idle",
        "T - Task",
        "H - Toggle help"
    ]
    
    # Calculate panel height
    panel_height = len(controls) * 20 + 10
    panel_y = SCREEN_HEIGHT - panel_height - 210  # Above event log
    
    # Draw background
    pygame.draw.rect(screen, (40, 40, 40), (10, panel_y, 280, panel_height))
    pygame.draw.rect(screen, WHITE, (10, panel_y, 280, panel_height), 2)
    
    # Draw controls
    y_offset = panel_y + 5
    for control in controls:
        control_text = small_font.render(control, True, WHITE)
        screen.blit(control_text, (15, y_offset))
        y_offset += 20
    


def draw_event_log():
    """Draw recent events log in bottom-left corner."""
    if not game_world or not hasattr(game_world, 'event_history'):
        return
    
    # Get recent events (last 8 events)
    recent_events = game_world.event_history[-8:] if game_world.event_history else []
    
    if not recent_events:
        return
    
    # Draw background panel
    log_panel_height = min(len(recent_events) * 22 + 30, 200)
    log_panel_y = SCREEN_HEIGHT - log_panel_height
    pygame.draw.rect(screen, (40, 40, 40), (10, log_panel_y, 580, log_panel_height))
    pygame.draw.rect(screen, WHITE, (10, log_panel_y, 580, log_panel_height), 2)
    
    # Draw header
    header_text = small_font.render("Recent Events:", True, WHITE)
    screen.blit(header_text, (15, log_panel_y + 5))
    
    # Draw events (most recent at bottom)
    y_offset = log_panel_y + 25
    for event in reversed(recent_events):  # Show most recent at bottom
        # Color code by action type
        if event.action == "kill":
            event_color = RED
        elif event.action == "sabo":
            event_color = (255, 165, 0)  # Orange
        elif event.action == "enter":
            event_color = BLUE
        elif event.action == "report":
            event_color = GREEN
        elif event.action == "say":
            event_color = (255, 255, 200)  # Light yellow
        else:
            event_color = WHITE
        
        # Format event text
        agent = game_world._get_agent_by_id(event.actor) if event.actor else None
        role_str = f"({agent.role})" if agent else ""
        
        if event.action == "say" and hasattr(event, 'statement') and event.statement:
            stmt = event.statement
            event_str = f"{event.actor}{role_str}: {stmt.predicate} {stmt.subject}={stmt.value}"
        elif event.action == "kill":
            # Try to find who was killed by checking dead agents at that location
            dead_at_location = [a for a in game_world.get_all_agents() 
                              if a.state == "dead" and a.location == event.location]
            if dead_at_location and len(dead_at_location) == 1:
                victim = dead_at_location[0]
                event_str = f"{event.actor}{role_str} KILLED {victim.id} at {event.location}"
            else:
                event_str = f"{event.actor}{role_str} KILLED someone at {event.location}"
        else:
            event_str = f"{event.actor}{role_str}: {event.action} at {event.location}"
        
        # Truncate if too long
        if len(event_str) > 55:
            event_str = event_str[:52] + "..."
        
        event_text = small_font.render(event_str, True, event_color)
        screen.blit(event_text, (15, y_offset))
        y_offset += 22
        
        # Don't draw more than can fit
        if y_offset >= SCREEN_HEIGHT - 5:
            break


def draw_brain_view(surface, agent_id):
    """
    Draw the brain view panel showing agent's DEL state.
    
    Shows:
    - Agent info (ID, role, state)
    - Kripke model (possible worlds count and details)
    - Suspicion scores
    - Recent memory/events
    """
    if not agent_id:
        # Draw empty panel
        panel_x = 600
        pygame.draw.rect(surface, DARK_GRAY, (panel_x, 0, SCREEN_WIDTH - panel_x, SCREEN_HEIGHT))
        placeholder = font.render("Click an agent to view brain", True, WHITE)
        surface.blit(placeholder, (panel_x + 20, SCREEN_HEIGHT // 2))
        return
    
    agent = game_world._get_agent_by_id(agent_id)
    if not agent:
        return
    
    # Define panel area
    panel_x = 600
    pygame.draw.rect(surface, DARK_GRAY, (panel_x, 0, SCREEN_WIDTH - panel_x, SCREEN_HEIGHT))
    
    y_offset = 20
    max_width = SCREEN_WIDTH - panel_x - 20
    
    # --- Agent Header ---
    state_color = GREEN if agent.state == "alive" else DEAD_COLOR
    header_text = f"Brain View: {agent.id} ({agent.role}) [{agent.state}]"
    header = font.render(header_text, True, state_color)
    surface.blit(header, (panel_x + 10, y_offset))
    y_offset += 40
    
    # --- Kripke Model: Possible Worlds ---
    worlds = agent.knowledge.get("worlds", [])
    num_worlds = len(worlds)
    
    worlds_header = font.render(f"Possible Worlds: {num_worlds}", True, WHITE)
    surface.blit(worlds_header, (panel_x + 10, y_offset))
    y_offset += 30
    
    # Visual bar for uncertainty (more worlds = more uncertainty)
    bar_width = min(num_worlds * 15, max_width - 20)
    bar_color = (100, 100, 255) if num_worlds > 1 else (100, 255, 100)
    pygame.draw.rect(surface, bar_color, (panel_x + 10, y_offset, bar_width, 20))
    y_offset += 40
    
    # Show actual world states (if not too many)
    if num_worlds > 0 and num_worlds <= 5:
        for i, world_state in enumerate(worlds):
            world_str = ", ".join([f"{aid}:{role}" for aid, role in world_state.items()])
            if len(world_str) > 60:
                world_str = world_str[:57] + "..."
            world_text = small_font.render(f"W{i+1}: {world_str}", True, (200, 200, 200))
            surface.blit(world_text, (panel_x + 10, y_offset))
            y_offset += 20
    elif num_worlds > 5:
        summary_text = small_font.render(f"({num_worlds} worlds - too many to display)", True, (150, 150, 150))
        surface.blit(summary_text, (panel_x + 10, y_offset))
        y_offset += 20
    
    y_offset += 10
    
    # --- Suspicion Levels (if NPC) ---
    if hasattr(agent, 'sus') and agent.sus:
        sus_header = font.render("Suspicion Levels:", True, WHITE)
        surface.blit(sus_header, (panel_x + 10, y_offset))
        y_offset += 30
        
        # Sort by suspicion (highest first)
        sorted_sus = sorted(agent.sus.items(), key=lambda x: x[1], reverse=True)
        
        for target_id, sus_val in sorted_sus:
            if target_id == agent.id:
                continue  # Skip self
            
            # Calculate bar length (scale to fit panel)
            max_sus = max(agent.sus.values()) if agent.sus.values() else 1.0
            bar_len = int((sus_val / max(1.0, max_sus)) * (max_width - 150))
            bar_len = min(bar_len, max_width - 150)
            
            # Color: green (low) -> yellow -> red (high)
            if sus_val < 0.3:
                bar_color = (0, 255, 0)
            elif sus_val < 0.7:
                bar_color = (255, 255, 0)
            else:
                bar_color = (255, 0, 0)
            
            # Draw agent ID and value
            name_text = small_font.render(f"{target_id}: {sus_val:.2f}", True, WHITE)
            surface.blit(name_text, (panel_x + 10, y_offset))
            
            # Draw suspicion bar
            pygame.draw.rect(surface, bar_color, (panel_x + 120, y_offset + 2, bar_len, 12))
            pygame.draw.rect(surface, WHITE, (panel_x + 120, y_offset + 2, max_width - 150, 12), 1)  # Border
            
            y_offset += 22
        
        y_offset += 10
    
    # --- Recent Memory/Events ---
    mem_header = font.render("Recent Memory:", True, WHITE)
    surface.blit(mem_header, (panel_x + 10, y_offset))
    y_offset += 30
    
    recent_memories = agent.knowledge.get("memory", [])[-5:]  # Last 5 memories
    
    if not recent_memories:
        no_mem_text = small_font.render("(No memories yet)", True, (150, 150, 150))
        surface.blit(no_mem_text, (panel_x + 10, y_offset))
    else:
        for mem in recent_memories:
            # Format memory item
            event = mem.event
            certainty_str = mem.certainty.name if hasattr(mem, 'certainty') else "UNKNOWN"
            source_str = mem.source_type if hasattr(mem, 'source_type') else "unknown"
            
            # Build memory string
            if event.action == "say" and hasattr(event, 'statement') and event.statement:
                stmt = event.statement
                mem_str = f"{event.action}: {stmt.predicate} {stmt.subject} = {stmt.value}"
            else:
                mem_str = f"{event.action} by {event.actor}"
            
            mem_str = f"[{certainty_str[:4]}] {mem_str}"
            
            # Color by certainty
            if certainty_str == "FACT":
                mem_color = (100, 255, 100)  # Green for facts
            elif certainty_str == "UNCERTAIN":
                mem_color = (255, 255, 100)  # Yellow for uncertain
            else:
                mem_color = (200, 200, 200)  # Gray for others
            
            # Truncate if too long
            if len(mem_str) > 50:
                mem_str = mem_str[:47] + "..."
            
            mem_text = small_font.render(mem_str, True, mem_color)
            surface.blit(mem_text, (panel_x + 10, y_offset))
            y_offset += 20
    
    y_offset += 10
    
    # --- Location Info ---
    loc_text = small_font.render(f"Location: {agent.location or 'None (dead/removed)'}", True, (200, 200, 200))
    surface.blit(loc_text, (panel_x + 10, y_offset))
    y_offset += 20
    
    # --- Connected Rooms ---
    if agent.location and game_world and hasattr(game_world, 'connections'):
        connected_rooms = game_world.get_connected_rooms(agent.location)
        if connected_rooms:
            conn_text = small_font.render(f"Can move to: {', '.join(connected_rooms)}", True, (150, 200, 255))
            surface.blit(conn_text, (panel_x + 10, y_offset))


def handle_player_action(action_name):
    """Handle a player action in player mode. For complex actions, prompts in console."""
    global game_world
    
    if not is_player_mode or not game_world or not game_world.player:
        return
    
    from actions import Actions
    
    if game_world.player.state != "alive":
        return
    
    # Process action based on type
    if action_name == "enter":
        # Show connected rooms and prompt in console
        connected_rooms = game_world.get_connected_rooms(game_world.player.location)
        print(f"\nConnected rooms from {game_world.player.location}: {', '.join(connected_rooms)}")
        target_room = input("Enter room name (or press Enter to cancel): ").strip()
        if target_room:
            event = Actions.apply(game_world, game_world.player, "enter", target_room)
            if event:
                print(f"Player moved to {target_room}")
            elif target_room not in connected_rooms:
                print(f"Error: {target_room} is not connected to current location!")
    
    elif action_name == "kill":
        # Get targets at current location
        targets = [a for a in game_world.get_agents_at_location(game_world.player.location) 
                  if a.id != game_world.player.id and a.state == "alive"]
        if not targets:
            print("No targets at this location!")
            return
        print(f"\nAvailable targets at {game_world.player.location}:")
        for i, target in enumerate(targets):
            print(f"  {i}: {target.id}")
        try:
            choice = input("Target number (or press Enter to cancel): ").strip()
            if choice:
                target_idx = int(choice)
                if 0 <= target_idx < len(targets):
                    event = Actions.apply(game_world, game_world.player, "kill", targets[target_idx].id)
                    if event:
                        print(f"Player killed {targets[target_idx].id}")
                else:
                    print("Invalid target index!")
        except ValueError:
            print("Invalid input!")
    
    elif action_name == "say":
        print("\nSay action format: predicate subject value")
        print("  predicate: role | location | did")
        print("  subject: agent_id")
        print("  value: the claim (e.g., 'bad', 'Engine', 'task')")
        
        predicate = input("Predicate (role/location/did): ").strip().lower()
        if predicate not in ["role", "location", "did"]:
            print(f"Invalid predicate: {predicate}")
            return
        
        alive_agents = game_world.get_alive_agents()
        print("\nAvailable agents:")
        for i, agent in enumerate(alive_agents):
            print(f"  {i}: {agent.id}")
        
        try:
            subject_choice = input("Subject (agent number or ID): ").strip()
            try:
                subject_idx = int(subject_choice)
                if 0 <= subject_idx < len(alive_agents):
                    subject = alive_agents[subject_idx].id
                else:
                    print("Invalid agent number!")
                    return
            except ValueError:
                subject = subject_choice
            
            value = input("Value: ").strip()
            if value:
                event = Actions.apply(game_world, game_world.player, "say", predicate, subject, value)
                if event:
                    print(f"Player said: {predicate} {subject} = {value}")
        except (ValueError, IndexError) as e:
            print(f"Invalid input: {e}")
    
    elif action_name == "report":
        event = Actions.apply(game_world, game_world.player, "report")
        if event:
            print("Player made a report")
    
    elif action_name == "sabo":
        event = Actions.apply(game_world, game_world.player, "sabo")
        if event:
            print("Player sabotaged")
    
    elif action_name == "idle":
        Actions.apply(game_world, game_world.player, "idle")
        print("Player is now idle")
    
    elif action_name == "task":
        Actions.apply(game_world, game_world.player, "task")
        print("Player is now doing a task")


def main_loop():
    """Main game loop for visualization."""
    global agent_positions, game_world, is_player_mode
    
    running = True
    selected_agent_id = None  # Currently selected agent for brain view
    
    while running:
        # --- A. Calculate Delta Time ---
        dt = clock.tick(FPS) / 1000.0  # Convert to seconds
        
        # --- B. Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Keyboard input for player actions (player mode only)
            elif event.type == pygame.KEYDOWN and is_player_mode and game_world.player:
                # Handle action key presses
                if event.key == pygame.K_e:
                    handle_player_action("enter")
                elif event.key == pygame.K_k:
                    handle_player_action("kill")
                elif event.key == pygame.K_s:
                    handle_player_action("say")
                elif event.key == pygame.K_r:
                    handle_player_action("report")
                elif event.key == pygame.K_b:
                    handle_player_action("sabo")
                elif event.key == pygame.K_i:
                    handle_player_action("idle")
                elif event.key == pygame.K_t:
                    handle_player_action("task")
            
            # Mouse click to select agent
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                selected_agent_id = None  # Reset selection
                
                # Check click on any agent (alive or dead)
                for agent_id, (agent_x, agent_y) in agent_positions.items():
                    # Agent circle radius is 15
                    distance_squared = (mouse_pos[0] - agent_x)**2 + (mouse_pos[1] - agent_y)**2
                    if distance_squared < 15**2:
                        selected_agent_id = agent_id
                        print(f"Selected agent: {agent_id}")
                        break
        
        # --- C. Game Logic Update ---
        # Update NPCs (they make decisions based on time)
        if not game_world.game_over():
            game_world.update_npcs(delta_time=dt)
        
        # --- D. Rendering ---
        screen.fill(DARK_BG)  # Dark background
        
        # Reset agent positions for this frame
        agent_positions = {}
        
        # 1. Draw room connections (lines) first, behind everything
        draw_room_connections()
        
        # 2. Draw rooms
        draw_rooms()
        
        # 3. Draw dead agents (corpses)
        draw_dead_agents()
        
        # 4. Draw alive agents
        draw_alive_agents()
        
        # 5. Draw brain view panel (right side)
        draw_brain_view(screen, selected_agent_id)
        
        # 6. Draw game info (turn, time, etc.)
        draw_game_info()
        
        # 6.5. Draw meeting banner (if in meeting phase)
        draw_meeting_banner()
        
        # 7. Draw player controls (if in player mode)
        draw_player_controls()
        
        # 8. Draw event log (bottom-left corner)
        draw_event_log()
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()


def show_mode_selection():
    """Show mode selection dialog and return the choice."""
    global screen
    
    selection = None
    running = True
    
    while running and selection is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    selection = "player"
                    running = False
                elif event.key == pygame.K_2:
                    selection = "simulation"
                    running = False
        
        # Draw mode selection screen
        screen.fill(DARK_BG)
        
        title = font.render("=== DEL-Game Visualizer ===", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 200))
        screen.blit(title, title_rect)
        
        mode1_text = font.render("1. Player Mode (you play as bad agent)", True, WHITE)
        mode1_rect = mode1_text.get_rect(center=(SCREEN_WIDTH // 2, 300))
        screen.blit(mode1_text, mode1_rect)
        
        mode2_text = font.render("2. Simulation Mode (all NPCs, no player)", True, WHITE)
        mode2_rect = mode2_text.get_rect(center=(SCREEN_WIDTH // 2, 350))
        screen.blit(mode2_text, mode2_rect)
        
        hint_text = small_font.render("Press 1 or 2 to choose", True, GRAY)
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, 450))
        screen.blit(hint_text, hint_rect)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    return selection


def main():
    """Initialize and start the visualizer."""
    global game_world, ROOM_COORDS, is_player_mode
    
    print("=== DEL-Game Visualizer ===")
    print("Click agents to view their DEL/Kripke model state")
    print("Close window to exit\n")
    
    # Show mode selection
    mode = show_mode_selection()
    if mode is None:
        pygame.quit()
        sys.exit()
    
    is_player_mode = (mode == "player")
    
    # Initialize game world based on mode
    if mode == "simulation":
        # Simulation mode: all NPCs, no player
        import random
        num_npcs = 5
        rooms = ["A", "B", "C", "D"]
        npcs = []
        
        # Create one bad NPC and rest good
        for i in range(num_npcs):
            role = "bad" if i == 0 else "good"
            npcs.append(NPC(f"npc{i}", role=role, location=random.choice(rooms)))
        
        game_world = World(num_npcs=0, seed=42, rooms=rooms, player=False, npcs=npcs)
        print(f"Starting in SIMULATION mode with {num_npcs} NPCs (1 bad, {num_npcs-1} good)")
    else:
        # Player mode (default)
        game_world = World(num_npcs=4, seed=42)
        print(f"Starting in PLAYER mode")
    
    # Generate room coordinates dynamically based on actual rooms
    ROOM_COORDS = generate_room_coords(game_world.rooms)
    
    print(f"Rooms: {game_world.rooms}")
    print(f"Starting visualization...\n")
    
    # Start main loop
    main_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nVisualization stopped by user")
        pygame.quit()
        sys.exit()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit()

