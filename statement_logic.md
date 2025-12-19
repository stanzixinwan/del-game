Cursor Prompt: Implement Advanced Mafia-Style Statement Logic
Context: I am building a social deduction game (like Among Us/Mafia) using Dynamic Epistemic Logic. I need to improve the NPC's decision-making process for what to say during meetings. Currently, choose_statement in npc_policy.py is too simple.

Objective: Refactor npc_policy.py to implement distinct, strategic statement generation logic for "Good" and "Bad" agents.

Requirements:

Refactor choose_statement:

Split the logic into two helper functions: _generate_good_statement(agent, world) and _generate_bad_statement(agent, world).

Ensure necessary imports are present (e.g., Statement from statement, Certainty from memory).

Implement _generate_good_statement (Truthful Detective Strategy):

Priority 1 - Direct Witness: Iterate through agent.knowledge["memory"]. If the agent has a FACT certainty memory of a "kill" event, they MUST return a statement accusing the killer (predicate="did", subject=killer_id, value="kill").

Priority 2 - High Suspicion: If agent.sus[target] > 0.8, accuse the target (predicate="role", value="bad").

Priority 3 - Info Sharing: Look for recent FACT memories of other agents entering rooms. Report the most recent sighting to help the group (predicate="location", subject=observed_agent, value=room_name).

Priority 4 - Self Alibi (Default): If none of the above, report their own current location truthfully (predicate="location", subject=self.id, value=self.location).

Implement _generate_bad_statement (Deceptive/Survival Strategy):

Priority 1 - Emergency Fake Alibi: Check world.get_dead_agents_at_location(agent.location). If there is a dead body in the current room (implying the agent might be the killer), they MUST lie. Return a statement placing themselves in a different random room.

Priority 2 - Framing (Random Chance ~30%): Pick a random "good" agent and accuse them (predicate="role", value="bad").

Priority 3 - Confusion (Random Chance ~30%): Lie about a good agent's location (e.g., say they were in a different room).

Priority 4 - Partner Vouching (Random Chance ~20%): If other bad agents exist, claim one of them is "good".

Priority 5 - Default Lie: Claim to be in a random room (that might or might not be the current one, but usually distinct to be safe).

Technical Constraints:

Use agent.knowledge.get("memory", []) to access memories.

Use mem.certainty and mem.event to filter facts.

Ensure Statement objects are correctly instantiated.

Do not break existing imports.