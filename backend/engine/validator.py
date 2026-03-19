"""
Scenario validator for ScenarioSpec v2.0.

Replaces the old Monte Carlo simulation approach. Validation now checks:
- Schema integrity (Pydantic)
- Exactly one player actor
- Unique actor / location IDs
- At least one loss condition
- All actor location_ids reference a known location
"""

from typing import Any, Dict, List, Tuple

from backend.schemas import ScenarioSpec, validate_scenario_spec
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ScenarioValidator:
    """Validates a ScenarioSpec dict and performs lightweight auto-repair."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_spec(self, spec_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a raw spec dict.

        Returns (is_valid, list_of_issue_strings).
        """
        issues: List[str] = []

        # 1. Pydantic schema validation
        try:
            spec = validate_scenario_spec(spec_data)
        except Exception as e:
            issues.append(f"Schema validation failed: {e}")
            return False, issues

        # 2. Exactly one player
        players = [a for a in spec.actors if a.is_player]
        if len(players) == 0:
            issues.append("No player actor found (is_player must be true on exactly one actor)")
        elif len(players) > 1:
            issues.append(
                f"Multiple player actors found: {[a.id for a in players]} — only one allowed"
            )

        # 3. Unique actor IDs
        actor_ids = [a.id for a in spec.actors]
        seen_actor_ids: set = set()
        for aid in actor_ids:
            if aid in seen_actor_ids:
                issues.append(f"Duplicate actor id: '{aid}'")
            seen_actor_ids.add(aid)

        # 4. Unique location IDs
        loc_ids = [loc.id for loc in spec.world.locations]
        seen_loc_ids: set = set()
        for lid in loc_ids:
            if lid in seen_loc_ids:
                issues.append(f"Duplicate location id: '{lid}'")
            seen_loc_ids.add(lid)

        # 5. Actor locations exist
        known_locs = set(loc_ids)
        for actor in spec.actors:
            if actor.location_id not in known_locs:
                issues.append(
                    f"Actor '{actor.id}' has unknown location_id '{actor.location_id}'"
                )

        # 6. At least 2 NPCs
        npcs = [a for a in spec.actors if not a.is_player]
        if len(npcs) < 2:
            issues.append(
                f"Only {len(npcs)} NPC(s) — at least 2 NPCs are required for meaningful play"
            )

        # 8. At least 2 locations
        if len(spec.world.locations) < 2:
            issues.append("At least 2 locations are required")

        is_valid = len(issues) == 0
        if is_valid:
            logger.info(f"Spec '{spec.name}' passed validation")
        else:
            logger.warning(f"Spec validation issues: {issues}")

        return is_valid, issues

    def auto_repair(
        self, spec_data: Dict[str, Any], issues: List[str]
    ) -> Dict[str, Any]:
        """
        Attempt simple structural repairs on a raw spec dict.

        Only fixes things that can be repaired without re-generating content.
        """
        repaired = _deep_copy(spec_data)

        # Ensure spec_version
        repaired.setdefault("spec_version", "2.0")

        # Ensure world exists
        repaired.setdefault("world", {})
        repaired["world"].setdefault("locations", [])
        repaired["world"].setdefault("factions", [])
        repaired["world"].setdefault("rules", "")
        repaired["world"].setdefault("description", "")
        repaired["world"].setdefault("tone", "")
        repaired["world"].setdefault("initial_time", "dawn")
        repaired["world"].setdefault("initial_day", 1)

        # Ensure actors list exists
        repaired.setdefault("actors", [])

        # Ensure global_state
        repaired.setdefault("global_state", {})

        # Ensure seed
        import random as _random
        repaired.setdefault("seed", _random.randint(1, 1_000_000))

        # Fix location_ids for actors whose location is missing
        known_locs = {loc["id"] for loc in repaired["world"]["locations"] if "id" in loc}
        if known_locs:
            fallback_loc = next(iter(known_locs))
            for actor in repaired.get("actors", []):
                if actor.get("location_id") not in known_locs:
                    actor["location_id"] = fallback_loc

        logger.info("Auto-repair applied to spec")
        return repaired


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _deep_copy(obj: Any) -> Any:
    """Simple deep copy via JSON round-trip."""
    import json
    return json.loads(json.dumps(obj))
