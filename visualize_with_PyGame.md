# PyGame Visualization Guide for DEL-Game

This guide provides step-by-step instructions for implementing a PyGame-based visualizer for the DEL-Game system. The visualizer displays agent locations, game state, and most importantly, the DEL/Kripke model internal states (possible worlds, suspicion scores, memory) for selected agents.

## Overview

The visualizer consists of:
- **Main game view**: Shows rooms and agents on the map
- **Brain view panel**: Shows selected agent's DEL state (Kripke worlds, suspicion, memory)
- **Interactive selection**: Click agents to view their cognitive state

---

## Step 1: Setup and Core Imports

```python
import pygame
import sys
# Import core game modules
from world import World
from actions import Actions
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
```

---

## Step 2: Room Coordinate Mapping

The game uses room names (like "A", "B", "C", "D"), but PyGame needs screen coordinates. We'll create a dynamic mapping function that works with any room configuration.

```python
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

# Initialize game world
# You can customize rooms here, or use default ["A", "B", "C", "D"]
game_world = World(num_npcs=4, seed=42)

# Generate room coordinates dynamically based on actual rooms
ROOM_COORDS = generate_room_coords(game_world.rooms)
```

**Note**: If you want to use custom named rooms, you can do:
```python
custom_rooms = ["Entrance", "Engine", "Storage", "Medbay"]
game_world = World(num_npcs=4, seed=42, rooms=custom_rooms)
ROOM_COORDS = generate_room_coords(custom_rooms)
```

---

## Step 3: Track Agent Screen Positions

We need to track where each agent is drawn on screen for accurate click detection.

```python
# Dictionary to store agent screen positions {agent_id: (x, y)}
agent_positions = {}
```

---

## Step 4: Main Game Loop

```python
def main_loop():
    global agent_positions
    running = True
    selected_agent_id = None  # Currently selected agent for brain view
    
    while running:
        # --- A. Calculate Delta Time ---
        dt = clock.tick(FPS) / 1000.0  # Convert to seconds
        
        # --- B. Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
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
        
        # 1. Draw rooms
        draw_rooms()
        
        # 2. Draw dead agents (corpses) first
        draw_dead_agents()
        
        # 3. Draw alive agents
        draw_alive_agents()
        
        # 4. Draw brain view panel (right side)
        draw_brain_view(screen, selected_agent_id)
        
        # 5. Draw game info (turn, time, etc.)
        draw_game_info()
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()
```

---

## Step 5: Drawing Functions

### Draw Rooms

```python
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
```

### Draw Dead Agents (Corpses)

```python
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
```

### Draw Alive Agents

```python
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
            
            # Color coding: Player = RED, NPC = BLUE
            if isinstance(agent, Player):
                color = RED
                # Add border for player
                pygame.draw.circle(screen, (255, 255, 255), (pos_x, pos_y), 17, 2)
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
```

### Draw Game Info

```python
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
```

---

## Step 6: Brain View (DEL State Visualization)

This is the core feature that visualizes the agent's epistemic state.

```python
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
```

---

## Step 7: Main Entry Point

```python
if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nVisualization stopped by user")
        pygame.quit()
        sys.exit()
```

---

## Complete File Structure

Put all the above code together in a file called `visualizer.py`. The complete file should:

1. Import all necessary modules
2. Define constants and initialize PyGame
3. Create the World instance
4. Generate room coordinates
5. Define all drawing functions
6. Define the main loop
7. Include the entry point

---

## Usage

### Running the Visualizer

```bash
python visualizer.py
```

### Features

- **Click agents** to view their DEL state (Kripke worlds, suspicion, memory)
- **Watch NPCs** make decisions in real-time
- **View game state** (turn, time, result)
- **See agent locations** on the map
- **Observe dead agents** (corpses) before they're reported

### Customization

- **Change room layout**: Modify `generate_room_coords()` function
- **Adjust colors**: Modify color constants at the top
- **Add more info**: Extend `draw_brain_view()` to show more DEL details
- **Player mode**: Add keyboard input handling to allow player actions

---

## Troubleshooting

1. **Agents not visible**: Check that `ROOM_COORDS` includes all rooms from `game_world.rooms`
2. **Click detection off**: Ensure `agent_positions` is updated in drawing functions
3. **Memory display empty**: Verify `agent.knowledge["memory"]` contains MemoryItem objects
4. **Suspicion not showing**: Only NPCs have `sus` attribute, not Player class

---

## Next Steps / Enhancements

1. **World state visualization**: Show actual world state distributions
2. **Statement display**: Show statements made during voting phase
3. **Event timeline**: Display chronological event history
4. **Player controls**: Add keyboard input for player actions
5. **Animation**: Smooth transitions when agents move
6. **Zoom/Pan**: Allow exploring larger maps
