import time

class Statement:
    """
    Represents a formal logical proposition made by an agent.
    Used for the SAY action to make claims about roles, locations, or actions.
    """
    
    def __init__(self, predicate, subject, value, speaker, timestamp=None):
        """
        Initialize a Statement.
        
        Args:
            predicate: "role" | "location" | "did"
            subject: agent_id that the statement is about
            value: the value/claim (e.g., "bad", "Engine", "task")
            speaker: agent_id who made the statement
            timestamp: time of statement (defaults to current time)
        """
        if predicate not in ["role", "location", "did"]:
            raise ValueError(f"Predicate must be 'role', 'location', or 'did', got: {predicate}")
        
        self.predicate = predicate  # "role" | "location" | "did"
        self.subject = subject      # agent_id
        self.value = value          # any value
        self.speaker = speaker      # agent_id who made the statement
        self.timestamp = timestamp if timestamp is not None else time.time()
    
    def __repr__(self):
        return f"Statement({self.speaker} says {self.subject}'s {self.predicate} is {self.value})"
    
    def __str__(self):
        return f"{self.speaker} says: {self.subject}'s {self.predicate} is {self.value}"
    
    def to_dict(self):
        """Convert statement to dictionary format."""
        return {
            "predicate": self.predicate,
            "subject": self.subject,
            "value": self.value,
            "speaker": self.speaker,
            "timestamp": self.timestamp
        }

