"""
Scenario compiler - converts specs to executable tools
"""

from typing import Any, Dict, List, Optional

from jsonschema import validate
from langchain.tools import BaseTool

from backend.schemas import Action, ScenarioSpec
from backend.schemas.outcome import StateChange
from backend.utils.jsonlogic import JSONLogicEvaluator


class ScenarioCompiler:
    """Compiles scenario specifications into executable tools"""

    def __init__(self, spec: ScenarioSpec):
        self.spec = spec
        self.tools: List[BaseTool] = []
        self._compile_utility_tools()

    def _compile_utility_tools(self):
        """Compile utility tools for agentic LLM behavior"""

        # Read state tool
        self.tools.append(self._create_read_state_tool())

        # Update state tool
        self.tools.append(self._create_update_state_tool())

        # Create character tool
        self.tools.append(self._create_character_tool())

        # Update world tool
        self.tools.append(self._create_update_world_tool())

        # Add memory tool
        self.tools.append(self._create_memory_tool())

        # Add semantic search tool
        self.tools.append(self._create_semantic_search_tool())

        # Add batch memory tool
        self.tools.append(self._create_batch_memory_tool())

        # Add stateful read tool with caching
        self.tools.append(self._create_stateful_read_tool())

    def _create_read_state_tool(self) -> BaseTool:
        """Create tool for reading game state"""

        class ReadStateTool(BaseTool):
            name: str = "read_state"
            description: str = (
                "Query the current game state at a specific path. Use this to check current values before making decisions."
            )

            def _run(self, path: str) -> str:
                """Read state at the given path"""
                try:
                    # Get the compiler instance
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "spec"):
                        return "Error: No state available"

                    # Simple path resolution
                    parts = path.split(".")
                    current = compiler.spec.state

                    for part in parts:
                        if part.startswith("[") and part.endswith("]"):
                            index = int(part[1:-1])
                            current = (
                                current[index]
                                if isinstance(current, list)
                                and 0 <= index < len(current)
                                else None
                            )
                        else:
                            current = (
                                current.get(part) if isinstance(current, dict) else None
                            )

                        if current is None:
                            break

                    return f"State at {path}: {current}"
                except Exception as e:
                    return f"Error reading state: {e}"

            async def _arun(self, path: str) -> str:
                """Async version of _run"""
                return self._run(path)

        tool = ReadStateTool()
        tool._compiler = self  # type: ignore # Attach reference to compiler
        return tool

    def _create_update_state_tool(self) -> BaseTool:
        """Create tool for updating game state"""

        class UpdateStateTool(BaseTool):
            name: str = "update_state"
            description: str = (
                "Modify the game state with set, inc, dec, mul, patch, push, pop, or addlog operations."
            )

            def _run(self, op: str, path: str, value: Any) -> str:
                """Update state with the given operation"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "spec"):
                        return "Error: No state available"

                    # Apply the state change
                    if op == "set":
                        compiler._set_value_at_path(path, value)
                    elif op == "inc":
                        current = compiler._get_value_at_path(path)
                        compiler._set_value_at_path(path, current + value)
                    elif op == "dec":
                        current = compiler._get_value_at_path(path)
                        compiler._set_value_at_path(path, current - value)
                    elif op == "mul":
                        current = compiler._get_value_at_path(path)
                        compiler._set_value_at_path(path, current * value)
                    elif op == "patch":
                        current = compiler._get_value_at_path(path)
                        if isinstance(current, dict) and isinstance(value, dict):
                            current.update(value)
                            compiler._set_value_at_path(path, current)
                    elif op == "push":
                        current = compiler._get_value_at_path(path)
                        if isinstance(current, list):
                            current.append(value)
                            compiler._set_value_at_path(path, current)
                    elif op == "pop":
                        current = compiler._get_value_at_path(path)
                        if isinstance(current, list) and len(current) > 0:
                            current.pop()
                            compiler._set_value_at_path(path, current)
                    elif op == "addlog":
                        current = compiler._get_value_at_path(path)
                        if isinstance(current, list):
                            current.append(value)
                            compiler._set_value_at_path(path, current)
                        else:
                            compiler._set_value_at_path(path, [value])
                    else:
                        return f"Unknown operation: {op}"

                    return f"State updated: {op} {path} = {value}"
                except Exception as e:
                    return f"Error updating state: {e}"

            async def _arun(self, op: str, path: str, value: Any) -> str:
                """Async version of _run"""
                return self._run(op, path, value)

        tool = UpdateStateTool()
        tool._compiler = self  # type: ignore
        return tool

    def _create_character_tool(self) -> BaseTool:
        """Create tool for adding new characters"""

        class CreateCharacterTool(BaseTool):
            name: str = "create_character"
            description: str = (
                "Add a NEW character/entity to the game world. Only use this for characters that don't exist yet. Provide id, type, name, and optionally background."
            )

            def _run(
                self, id: str, type: str, name: str, background: Optional[str] = None
            ) -> str:
                """Create a new character"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "spec"):
                        return "Error: No state available"

                    # Check if entity already exists
                    for entity in compiler.spec.entities:
                        if entity.get("id") == id:
                            return f"Error: Character with id '{id}' already exists. Use their existing id instead of creating a duplicate."

                    # Build entity data
                    entity_data = {"id": id, "type": type, "name": name}
                    if background:
                        entity_data["background"] = background

                    # Add to entities list
                    compiler.spec.entities.append(entity_data)

                    # Also add to state.entities if it exists
                    state_entities = compiler._get_value_at_path("entities")
                    if isinstance(state_entities, list):
                        state_entities.append(entity_data)
                        compiler._set_value_at_path("entities", state_entities)

                    return f"Character created: {name} ({id}) - {type}"
                except Exception as e:
                    return f"Error creating character: {e}"

            async def _arun(
                self, id: str, type: str, name: str, background: Optional[str] = None
            ) -> str:
                """Async version of _run"""
                return self._run(id, type, name, background)

        tool = CreateCharacterTool()
        tool._compiler = self  # type: ignore
        return tool

    def _create_update_world_tool(self) -> BaseTool:
        """Create tool for updating world state"""

        class UpdateWorldTool(BaseTool):
            name: str = "update_world"
            description: str = (
                "Update world state like time, weather, locations, etc. Provide key-value pairs as separate parameters (e.g., time_of_day='evening', weather='rainy')."
            )

            def _run(self, **kwargs) -> str:
                """Update world state with any key-value pairs"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "spec"):
                        return "Error: No state available"

                    if not kwargs:
                        return "No changes provided"

                    # Apply changes to world state
                    world_state = compiler._get_value_at_path("world")
                    if not isinstance(world_state, dict):
                        world_state = {}

                    world_state.update(kwargs)
                    compiler._set_value_at_path("world", world_state)

                    return f"World updated: {kwargs}"
                except Exception as e:
                    return f"Error updating world: {e}"

            async def _arun(self, **kwargs) -> str:
                """Async version of _run"""
                return self._run(**kwargs)

        tool = UpdateWorldTool()
        tool._compiler = self  # type: ignore
        return tool

    def _create_memory_tool(self) -> BaseTool:
        """Create tool for adding memories"""

        class AddMemoryTool(BaseTool):
            name: str = "add_memory"
            description: str = (
                "Record a memory for an entity. Specify entity_id, content, and visibility (private or public). "
                "🔗 PRIORITIZE relationship memories when characters interact! "
                "Use scope='relationship' for interactions between characters. "
                "Include keywords: 'trust', 'fear', 'love', 'alliance', 'rivalry' for auto-relationship extraction. "
                "Examples: add_memory(entity_id='elena', content='Growing to trust Marcus after the rescue', visibility='private', scope='relationship')"
            )

            def _run(
                self,
                entity_id: str,
                content: str,
                visibility: str = "private",
                scope: str = "general",
            ) -> str:
                """Add memory for entity with optional scope"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "_orchestrator"):
                        return "Error: No orchestrator available"

                    orchestrator = compiler._orchestrator

                    # Determine related entities for relationship memories
                    related_entities = []
                    if scope == "relationship":
                        # Extract potential entity names from content
                        entity_names = []
                        if (
                            hasattr(orchestrator.spec, "entities")
                            and orchestrator.spec.entities
                        ):
                            entity_names = [
                                e.get("name", e.get("id", ""))
                                for e in orchestrator.spec.entities
                                if e.get("name") or e.get("id")
                            ]

                        # Look for other entity names mentioned in the content
                        for name in entity_names:
                            if name != entity_id and name.lower() in content.lower():
                                related_entities.append(name)

                    # Use scoped memory system for better organization
                    from backend.engine.memory import MemoryVisibility

                    vis_enum = "private" if visibility == "private" else "public"

                    orchestrator.memory.update_scoped_memory(
                        entity_id=entity_id,
                        content=content,
                        scope=scope,
                        visibility=vis_enum,
                        related_entities=related_entities if related_entities else None,
                    )

                    scope_indicator = f" ({scope})" if scope != "general" else ""
                    return f"Memory added for {entity_id}{scope_indicator}: {content[:50]}..."
                except Exception as e:
                    return f"Error adding memory: {e}"

            async def _arun(
                self,
                entity_id: str,
                content: str,
                visibility: str = "private",
                scope: str = "general",
            ) -> str:
                """Async version of _run"""
                return self._run(entity_id, content, visibility, scope)

        tool = AddMemoryTool()
        tool._compiler = self  # type: ignore
        return tool

    def _create_semantic_search_tool(self) -> BaseTool:
        """Create tool for semantic memory search"""

        class SemanticSearchTool(BaseTool):
            name: str = "search_memories"
            description: str = (
                "Search memories using semantic similarity. Query by meaning rather than exact keywords. "
                "Args: query (required), entity_id (optional), scope (optional), limit (optional, default 5), threshold (optional, default 0.1)"
            )

            def _run(
                self,
                query: str,
                entity_id: Optional[str] = None,
                scope: Optional[str] = None,
                limit: int = 5,
                threshold: float = 0.1,
            ) -> str:
                """Search memories semantically"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "_orchestrator"):
                        return "Error: No orchestrator available"

                    orchestrator = compiler._orchestrator

                    # Search memories
                    results = orchestrator.memory.search_memories_semantic(
                        query=query,
                        entity_id=entity_id,
                        scope=scope,
                        limit=limit,
                        threshold=threshold,
                    )

                    if not results:
                        return f"No memories found for query: {query}"

                    # Format results
                    result_lines = [
                        f"Found {len(results)} relevant memories for '{query}':"
                    ]
                    for i, result in enumerate(results, 1):
                        similarity = result.get("similarity", 0)
                        content = result.get("content", "")
                        metadata = result.get("metadata", {})

                        result_lines.append(
                            f"{i}. [{metadata.get('scope', 'unknown')}] {content[:100]}{'...' if len(content) > 100 else ''} "
                            f"(similarity: {similarity:.3f}, entity: {metadata.get('entity_id', 'unknown')})"
                        )

                    return "\n".join(result_lines)

                except Exception as e:
                    return f"Error searching memories: {e}"

            async def _arun(
                self,
                query: str,
                entity_id: Optional[str] = None,
                scope: Optional[str] = None,
                limit: int = 5,
                threshold: float = 0.1,
            ) -> str:
                """Async version of _run"""
                return self._run(query, entity_id, scope, limit, threshold)

        tool = SemanticSearchTool()
        tool._compiler = self  # type: ignore
        return tool

    def _create_batch_memory_tool(self) -> BaseTool:
        """Create tool for batch memory updates"""

        class BatchMemoryTool(BaseTool):
            name: str = "add_memories"
            description: str = (
                "Add multiple memories in a single call to reduce tool usage. "
                "Accepts a list of memory objects with entity_id, content, visibility, and scope. "
                "Use this for relationship tracking: include 'trust', 'fear', 'love', 'alliance' keywords in content. "
                "Examples: add_memories([{entity_id: 'elena', content: 'Growing to trust Marcus after rescue', visibility: 'private', scope: 'relationship'}])"
            )

            def _run(
                self,
                memories: List[Dict[str, Any]],
            ) -> str:
                """Add multiple memories at once"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler or not hasattr(compiler, "_orchestrator"):
                        return "Error: No orchestrator available"

                    orchestrator = compiler._orchestrator
                    results = []

                    for memory in memories:
                        entity_id = memory.get("entity_id")
                        content = memory.get("content", "")
                        visibility = memory.get("visibility", "private")
                        scope = memory.get("scope", "general")

                        if not entity_id or not content:
                            results.append(f"Skipped invalid memory: {memory}")
                            continue

                        # Use the existing memory tool logic
                        vis_enum = "private" if visibility == "private" else "public"

                        orchestrator.memory.update_scoped_memory(
                            entity_id=entity_id,
                            content=content,
                            scope=scope,  # type: ignore
                            visibility=vis_enum,
                        )

                        results.append(
                            f"Memory added for {entity_id} ({scope}): {content[:50]}..."
                        )

                    return f"Batch memory update completed. {len(results)} memories processed."

                except Exception as e:
                    return f"Error in batch memory update: {e}"

            async def _arun(
                self,
                memories: List[Dict[str, Any]],
            ) -> str:
                """Async version of _run"""
                return self._run(memories)

        tool = BatchMemoryTool()
        tool._compiler = self  # type: ignore
        return tool

    def _create_stateful_read_tool(self) -> BaseTool:
        """Create tool for reading game state with caching"""

        class StatefulReadTool(BaseTool):
            name: str = "read_state_cached"
            description: str = (
                "Read game state with caching for recent values. Use use_cache=True to avoid repeated reads. "
                "Examples: read_state_cached('state.player.health', use_cache=True)"
            )

            def _run(
                self,
                path: str,
                use_cache: bool = True,
            ) -> str:
                """Read state value with optional caching"""
                try:
                    compiler = getattr(self, "_compiler", None)
                    if not compiler:
                        return "Error: No compiler available"

                    # Check cache first if requested
                    if use_cache:
                        # Simple in-memory cache per compiler instance
                        cache_key = f"state_cache_{path}"
                        if hasattr(compiler, cache_key):
                            cached_value = getattr(compiler, cache_key)
                            return f"Cached: {cached_value}"

                    # Get fresh value
                    value = compiler._get_value_at_path(path)

                    # Cache the value if requested
                    if use_cache:
                        setattr(compiler, cache_key, value)

                    return f"{value}" if value is not None else "null"

                except Exception as e:
                    return f"Error reading state: {e}"

            async def _arun(
                self,
                path: str,
                use_cache: bool = True,
            ) -> str:
                """Async version of _run"""
                return self._run(path, use_cache)

        tool = StatefulReadTool()
        tool._compiler = self  # type: ignore
        return tool

    def _get_value_at_path(self, path: str) -> Any:
        """Get value at JSON pointer path"""
        if not path or path == "":
            return self.spec.state

        parts = path.split(".")
        current = self.spec.state

        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                index = int(part[1:-1])
                current = (
                    current[index]  # type: ignore
                    if isinstance(current, list) and 0 <= index < len(current)
                    else None
                )
            else:
                current = current.get(part) if isinstance(current, dict) else None  # type: ignore

            if current is None:
                break

        return current

    def _set_value_at_path(self, path: str, value: Any):
        """Set value at JSON pointer path"""
        if not path or path == "":
            self.spec.state = value  # type: ignore
            return

        parts = path.split(".")
        current: Any = self.spec.state

        for i, part in enumerate(parts[:-1]):
            if part.startswith("[") and part.endswith("]"):
                index = int(part[1:-1])
                if not isinstance(current, list) or index >= len(current):
                    return
                current = current[index]
            else:
                if not isinstance(current, dict):
                    return
                if part not in current:
                    current[part] = {}
                current = current[part]

        final_part = parts[-1]
        if final_part.startswith("[") and final_part.endswith("]"):
            index = int(final_part[1:-1])
            if isinstance(current, list) and 0 <= index < len(current):
                current[index] = value
        else:
            if isinstance(current, dict):
                current[final_part] = value

    def get_tools(self) -> List[BaseTool]:
        """Get compiled tools"""
        return self.tools
