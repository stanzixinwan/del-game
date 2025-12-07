import time

class Event:
    """Represents an event in the game with action, actor, location, witnesses, timestamp, and visibility."""
    
    def __init__(self, action, actor, location, witnesses=None, visibility="private", timestamp=None, statement=None):
        """
        Initialize an event.
        
        Args:
            action: "kill" | "sabo" | "enter" | "report" | "say"
            actor: agent id who performed the action
            location: room name where event occurred
            witnesses: list of agent ids who witnessed the event (None for private)
            visibility: "private" | "witnessed" | "public"
            timestamp: time of event (defaults to current time)
            statement: Statement object (only for "say" actions)
        """
        self.action = action
        self.actor = actor
        self.location = location
        self.witnesses = witnesses if witnesses is not None else []
        self.visibility = visibility
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.statement = statement  # Statement object for "say" actions
    
    def __repr__(self):
        if self.statement:
            return f"Event({self.action}, {self.actor}, {self.location}, visibility={self.visibility}, statement={self.statement})"
        return f"Event({self.action}, {self.actor}, {self.location}, visibility={self.visibility})"

