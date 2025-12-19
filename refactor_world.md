Cursor Prompt: Refactor World for Asynchronous/Phased Simulation
Context: I have a PyGame visualizer (visualizer.py) running a World simulation (world.py). Currently, world.update_npcs() runs real-time logic. However, when a "Meeting/Voting" event occurs (triggered by Actions.report), the function world.conduct_vote() runs synchronously and instantaneously. This means the player cannot see the voting process (statements, voting, results) visually—it all happens in a single frame.

Objective: Refactor world.py to implement a State Machine for the game loop, allowing the Voting Phase to play out slowly over time (e.g., one agent speaks every 2 seconds).

Specific Tasks:

Add Game States to World class:

Add self.phase attribute. Enum values: PHASE_PLAYING (normal movement), PHASE_MEETING (voting).

Add self.meeting_timer and self.meeting_step to track progress during a meeting.

Refactor conduct_vote -> start_meeting:

Instead of running the full logic immediately, start_meeting(reporter_id) should just:

Set self.phase = PHASE_MEETING.

Teleport all agents to the "Admin" room (or a central location).

Initialize self.meeting_queue (list of agents who need to speak/vote).

Implement update_meeting(delta_time):

Create this new method to handle logic when self.phase == PHASE_MEETING.

Use a timer. Every 2.0 seconds (simulated time), process the next step:

Step 1 (Statements): Pop an agent from the queue, let them choose_statement() and create a SAY event.

Step 2 (Voting): Once all spoke, let everyone cast a vote.

Step 3 (Result): Calculate result, execute ejection (kill), and return self.phase to PHASE_PLAYING.

Update visualizer.py:

In the main loop, check game_world.phase.

If PHASE_MEETING, draw a "MEETING IN PROGRESS" banner at the top.

Ensure update_npcs delegates to update_meeting when appropriate.

Constraints:

Do not break the existing Kripke Model logic (update_belief calls must still happen when events are generated).

Keep the PyGame loop non-blocking.