class Room:
    """
    Room class for location representation.
    
    Stores room name, connectivity to other rooms, and agents currently in the room.
    """
    
    def __init__(self, name, connected_rooms=None):
        """
        Initialize a room.
        
        Args:
            name: room name (string identifier)
            connected_rooms: list of room names that this room connects to (default: empty list)
        """
        self.name = name
        self.connected_rooms = connected_rooms if connected_rooms is not None else []
        self.agents = []  # List of Agent objects currently in this room
        self.dead_agents = []  # List of dead Agent objects (corpses) in this room
    
    def add_agent(self, agent):
        """
        Add an agent to this room.
        
        Args:
            agent: Agent instance to add
        """
        if agent.state == "dead":
            if agent not in self.dead_agents:
                self.dead_agents.append(agent)
        else:
            if agent not in self.agents:
                self.agents.append(agent)
    
    def remove_agent(self, agent):
        """
        Remove an agent from this room.
        
        Args:
            agent: Agent instance to remove
        """
        if agent in self.agents:
            self.agents.remove(agent)
        if agent in self.dead_agents:
            self.dead_agents.remove(agent)
    
    def get_agents(self, alive_only=True):
        """
        Get agents in this room.
        
        Args:
            alive_only: if True, return only alive agents; if False, return all agents
        
        Returns:
            List of Agent objects
        """
        if alive_only:
            return self.agents.copy()
        else:
            return self.agents.copy() + self.dead_agents.copy()
    
    def get_dead_agents(self):
        """
        Get dead agents (corpses) in this room.
        
        Returns:
            List of dead Agent objects
        """
        return self.dead_agents.copy()
    
    def is_connected_to(self, room_name):
        """
        Check if this room is connected to another room.
        
        Args:
            room_name: name of the room to check connection to
        
        Returns:
            True if connected, False otherwise
        """
        return room_name in self.connected_rooms
    
    def add_connection(self, room_name):
        """
        Add a connection to another room.
        
        Args:
            room_name: name of the room to connect to
        """
        if room_name not in self.connected_rooms:
            self.connected_rooms.append(room_name)
    
    def remove_connection(self, room_name):
        """
        Remove a connection to another room.
        
        Args:
            room_name: name of the room to disconnect from
        """
        if room_name in self.connected_rooms:
            self.connected_rooms.remove(room_name)
    
    def get_connected_rooms(self):
        """
        Get list of room names this room is connected to.
        
        Returns:
            List of room name strings
        """
        return self.connected_rooms.copy()
    
    def __str__(self):
        """String representation of the room."""
        return f"Room({self.name})"
    
    def __repr__(self):
        """String representation for debugging."""
        return f"Room(name='{self.name}', connected_to={self.connected_rooms}, agents={len(self.agents)}, dead={len(self.dead_agents)})"
    
    def __eq__(self, other):
        """Equality comparison by name."""
        if isinstance(other, Room):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        return False
    
    def __hash__(self):
        """Hash based on name for use in sets/dicts."""
        return hash(self.name)

