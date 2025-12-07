from enum import Enum

class Certainty(Enum):
    FACT = 1         # Hard Evidence. Observed directly or Public event. Cannot be overridden.
    UNCERTAIN = 2    # Soft Evidence. Hearsay/Claims from others. Subject to verification.
    VERIFIED = 3     # Trusted. Hearsay that has been corroborated by Facts.
    DISPROVED = 4    # Lie Detected. Hearsay that contradicts a Fact. (Triggers High Sus)

class MemoryItem:
    """
    Wrapper for atomic, instant events (e.g., "I saw NPC1 KILL NPC2" or "Player SAID 'I am good'").
    Designed to support Dynamic Epistemic Logic (DEL) by separating objective reality from subjective beliefs.
    """
    
    def __init__(self, event, source_type, source_id=None):
        """
        Initialize a MemoryItem.
        
        Args:
            event: Reference to original global Event object
            source_type: "observation" | "hearsay"
            source_id: Who claimed this? (Only for hearsay, defaults to None)
        """
        self.event = event                  # Reference to original global Event
        self.source_type = source_type      # "observation" | "hearsay"
        self.source_id = source_id          # Who claimed this? (Only for hearsay)
        
        # Initial Certainty Logic:
        # If source_type == "observation" -> Certainty.FACT
        # If source_type == "hearsay"     -> Certainty.UNCERTAIN
        self.certainty = self._determine_initial_certainty()
        
        self.time_start = event.timestamp
    
    def _determine_initial_certainty(self):
        """Determine initial certainty based on source type."""
        if self.source_type == "observation":
            return Certainty.FACT
        elif self.source_type == "hearsay":
            return Certainty.UNCERTAIN
        else:
            # Default to uncertain for unknown source types
            return Certainty.UNCERTAIN
    
    def __repr__(self):
        source_info = f"from {self.source_id}" if self.source_id else "direct"
        return f"MemoryItem({self.source_type}, {self.certainty.name}, {source_info}, event={self.event.action})"