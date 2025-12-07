Memory System Specification

This document defines the architecture for the Agent Memory System, specifically designed to support Dynamic Epistemic Logic (DEL). It separates objective reality (Facts) from subjective beliefs (Hearsay) and handles incomplete temporal observations.

1. Core Philosophy

The knowledge["memory"] list in Agent should no longer store raw Event objects directly. Instead, it must store wrapper objects (MemoryItem or ObservationRecord) that encapsulate the subjective certainty and source of the information.

2. Data Structures

2.1 Certainty Enum

Defines the agent's trust level in a specific piece of memory.

from enum import Enum

class Certainty(Enum):
    FACT = 1         # Hard Evidence. Observed directly or Public event. Cannot be overridden.
    UNCERTAIN = 2    # Soft Evidence. Hearsay/Claims from others. Subject to verification.
    VERIFIED = 3     # Trusted. Hearsay that has been corroborated by Facts.
    DISPROVED = 4    # Lie Detected. Hearsay that contradicts a Fact. (Triggers High Sus)


2.2 MemoryItem (For Discrete Events)

Wrapper for atomic, instant events (e.g., "I saw NPC1 KILL NPC2" or "Player SAID 'I am good'").

class MemoryItem:
    def __init__(self, event, source_type, source_id=None):
        self.event = event                  # Reference to original global Event
        self.source_type = source_type      # "observation" | "hearsay"
        self.source_id = source_id          # Who claimed this? (Only for hearsay)
        
        # Initial Certainty Logic:
        # If source_type == "observation" -> Certainty.FACT
        # If source_type == "hearsay"     -> Certainty.UNCERTAIN
        self.certainty = self._determine_initial_certainty()
        
        self.time_start = event.timestamp
