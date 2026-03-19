"""
Memory system — writes, retrieves, and summarizes actor memories.

Three responsibilities:
  1. write_memories()    Store new MemoryEntry records from a turn's output.
  2. retrieve()          Handled by ContextBuilder — memory.py just writes.
  3. maybe_summarize()   Every N turns, distill older memories into known_facts
                         on the actor's card (Tier 2), keeping context compact.

The summarizer is the key to long-term memory: events from turn 1 survive
at turn 50 as bullet points in known_facts, not as raw log entries.
"""

from typing import Any, Dict, List

from langchain.schema import HumanMessage

from backend.config import settings
from backend.db.manager import DatabaseManager
from backend.schemas.turn import MemoryEntry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """Writes and summarizes actor memories."""

    def __init__(self, db: DatabaseManager, provider: Any):
        """
        Args:
            db:       Database manager for reading/writing memory entries and actor state.
            provider: LLM provider used by the summarizer.
        """
        self.db = db
        self.provider = provider

    # ------------------------------------------------------------------ #
    # Writing                                                              #
    # ------------------------------------------------------------------ #

    def write_memories(self, session_id: str, turn: int,
                       entries: List[MemoryEntry]) -> None:
        """
        Persist a list of MemoryEntry records from a turn.

        Public memories (world events everyone knows) are also written for
        every NPC in the session, so they all learn about major events.
        """
        public_entries = [e for e in entries if e.visibility == "public"]
        private_entries = [e for e in entries if e.visibility != "public"]

        for entry in private_entries:
            self.db.add_memory(
                session_id=session_id,
                actor_id=entry.actor_id,
                turn=turn,
                content=entry.content,
                tags=entry.tags,
                visibility="private",
            )
            logger.debug(f"[Memory] Turn {turn} — {entry.actor_id}: {entry.content[:60]}...")

        # Fan public memories out to all actors in the session
        if public_entries:
            all_actors = self.db.get_all_actors(session_id)
            for entry in public_entries:
                for actor in all_actors:
                    self.db.add_memory(
                        session_id=session_id,
                        actor_id=actor["actor_id"],
                        turn=turn,
                        content=entry.content,
                        tags=entry.tags,
                        visibility="public",
                    )
            logger.debug(
                f"[Memory] Turn {turn} — broadcast {len(public_entries)} public "
                f"memories to {len(all_actors)} actors"
            )

    def write_npc_thought(self, session_id: str, actor_id: str,
                          turn: int, thought: str, tags: List[str]) -> None:
        """Store an NPC's private_thought as a memory."""
        self.db.add_memory(
            session_id=session_id,
            actor_id=actor_id,
            turn=turn,
            content=thought,
            tags=tags,
            visibility="private",
        )

    # ------------------------------------------------------------------ #
    # Summarization                                                        #
    # ------------------------------------------------------------------ #

    async def maybe_summarize(self, session_id: str, current_turn: int) -> None:
        """
        Run the summarizer if we've hit the interval.

        Called once per turn after all memories are written.
        On the interval, summarizes older memories for every actor and
        updates their known_facts (Tier 2).
        """
        if current_turn == 0 or current_turn % settings.memory_summary_interval != 0:
            return

        logger.info(
            f"[Memory] Turn {current_turn} — running summarizer "
            f"(interval: {settings.memory_summary_interval})"
        )
        actors = self.db.get_all_actors(session_id)
        for actor in actors:
            await self._summarize_actor(session_id, actor, current_turn)

    async def _summarize_actor(self, session_id: str, actor: Dict[str, Any],
                               current_turn: int) -> None:
        """
        For one actor, distill old memories into known_facts.

        Takes all memories older than (current_turn - summary_interval),
        combines them with existing known_facts, and asks the LLM to produce
        a tighter bullet-point list. Updates the actor's known_facts in DB.
        """
        cutoff = current_turn - settings.memory_summary_interval
        old_memories = self.db.get_memories_older_than(session_id, actor["actor_id"], cutoff)

        if not old_memories:
            return

        existing_facts = actor.get("known_facts", [])
        memory_text = "\n".join(
            f"[Turn {m['turn']}] {m['content']}" for m in old_memories
        )
        existing_facts_text = "\n".join(f"- {f}" for f in existing_facts)

        prompt = _build_summarizer_prompt(
            actor_name=actor["name"],
            existing_facts=existing_facts_text,
            new_memories=memory_text,
        )

        try:
            result = await self.provider.chat([HumanMessage(content=prompt)])
            new_facts = _parse_facts(result.content)
            self.db.save_actor(session_id, actor["actor_id"], {"known_facts": new_facts})
            logger.info(
                f"[Memory] Summarized {len(old_memories)} memories for {actor['name']} "
                f"→ {len(new_facts)} known facts"
            )
        except Exception as e:
            logger.error(f"[Memory] Summarizer failed for {actor['actor_id']}: {e}")


# ------------------------------------------------------------------ #
# Prompt helpers                                                       #
# ------------------------------------------------------------------ #

def _build_summarizer_prompt(actor_name: str, existing_facts: str,
                              new_memories: str) -> str:
    return f"""You are updating {actor_name}'s long-term memory.

Existing known facts:
{existing_facts if existing_facts else "(none yet)"}

New memories to integrate:
{new_memories}

Produce a concise bullet-point list of what {actor_name} now knows and remembers.
Rules:
- Merge overlapping facts; don't repeat
- Keep facts specific and concrete (names, places, events, relationships)
- Remove facts that are no longer relevant
- Maximum 15 bullet points
- Output ONLY the bullet points, one per line, starting with "- "
- No preamble, no explanation"""


def _parse_facts(response: str) -> List[str]:
    """Extract bullet points from the LLM response."""
    facts = []
    for line in response.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            facts.append(line[2:].strip())
        elif line.startswith("* "):
            facts.append(line[2:].strip())
        elif line:
            facts.append(line)
    return facts[:15]  # Hard cap to keep known_facts compact
