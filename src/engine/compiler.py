"""
Scenario compiler - converts specs to executable tools
"""

from typing import Dict, Any, List
from langchain.tools import BaseTool
from src.schemas import ScenarioSpec, Action
from src.utils.jsonlogic import JSONLogicEvaluator
from src.schemas.outcome import StateChange
from jsonschema import validate


class ScenarioCompiler:
    """Compiles scenario specifications into executable tools"""
    
    def __init__(self, spec: ScenarioSpec):
        self.spec = spec
        self.tools = []
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
    
    def _create_read_state_tool(self) -> BaseTool:
        """Create tool for reading game state"""
        
        class ReadStateTool(BaseTool):
            name: str = "read_state"
            description: str = "Query the current game state at a specific path. Use this to check current values before making decisions."
            
            def _run(self, path: str) -> str:
                """Read state at the given path"""
                try:
                    # Get the compiler instance
                    compiler = getattr(self, '_compiler', None)
                    if not compiler or not hasattr(compiler, 'spec'):
                        return "Error: No state available"
                    
                    # Simple path resolution
                    parts = path.split(".")
                    current = compiler.spec.state
                    
                    for part in parts:
                        if part.startswith("[") and part.endswith("]"):
                            index = int(part[1:-1])
                            current = current[index] if isinstance(current, list) and 0 <= index < len(current) else None
                        else:
                            current = current.get(part) if isinstance(current, dict) else None
                        
                        if current is None:
                            break
                    
                    return f"State at {path}: {current}"
                except Exception as e:
                    return f"Error reading state: {e}"
            
            async def _arun(self, path: str) -> str:
                """Async version of _run"""
                return self._run(path)
        
        tool = ReadStateTool()
        tool._compiler = self  # Attach reference to compiler
        return tool
    
    def _create_update_state_tool(self) -> BaseTool:
        """Create tool for updating game state"""
        
        class UpdateStateTool(BaseTool):
            name: str = "update_state"
            description: str = "Modify the game state with set, inc, dec, mul, patch, push, pop, or addlog operations."
            
            def _run(self, op: str, path: str, value: Any) -> str:
                """Update state with the given operation"""
                try:
                    compiler = getattr(self, '_compiler', None)
                    if not compiler or not hasattr(compiler, 'spec'):
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
        tool._compiler = self
        return tool
    
    def _create_character_tool(self) -> BaseTool:
        """Create tool for adding new characters"""
        
        class CreateCharacterTool(BaseTool):
            name: str = "create_character"
            description: str = "Add a NEW character/entity to the game world. Only use this for characters that don't exist yet. Provide id, type, name, and optionally background."
            
            def _run(self, id: str, type: str, name: str, background: str = None) -> str:
                """Create a new character"""
                try:
                    compiler = getattr(self, '_compiler', None)
                    if not compiler or not hasattr(compiler, 'spec'):
                        return "Error: No state available"
                    
                    # Check if entity already exists
                    for entity in compiler.spec.entities:
                        if entity.get('id') == id:
                            return f"Error: Character with id '{id}' already exists. Use their existing id instead of creating a duplicate."
                    
                    # Build entity data
                    entity_data = {
                        "id": id,
                        "type": type,
                        "name": name
                    }
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
            
            async def _arun(self, id: str, type: str, name: str, background: str = None) -> str:
                """Async version of _run"""
                return self._run(id, type, name, background)
        
        tool = CreateCharacterTool()
        tool._compiler = self
        return tool
    
    def _create_update_world_tool(self) -> BaseTool:
        """Create tool for updating world state"""
        
        class UpdateWorldTool(BaseTool):
            name: str = "update_world"
            description: str = "Update world state like time, weather, locations, etc. Provide key-value pairs as separate parameters (e.g., time_of_day='evening', weather='rainy')."
            
            def _run(self, **kwargs) -> str:
                """Update world state with any key-value pairs"""
                try:
                    compiler = getattr(self, '_compiler', None)
                    if not compiler or not hasattr(compiler, 'spec'):
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
        tool._compiler = self
        return tool
    
    def _create_memory_tool(self) -> BaseTool:
        """Create tool for adding memories"""
        
        class AddMemoryTool(BaseTool):
            name: str = "add_memory"
            description: str = "Record a memory for an entity. Specify entity_id, content, and visibility (private or public)."
            
            def _run(self, entity_id: str, content: str, visibility: str = "private") -> str:
                """Add memory for entity"""
                try:
                    compiler = getattr(self, '_compiler', None)
                    if not compiler or not hasattr(compiler, '_orchestrator'):
                        return "Error: No orchestrator available"
                    
                    orchestrator = compiler._orchestrator
                    
                    # Add to memory
                    if visibility == "private":
                        orchestrator.memory.update_private_memory(entity_id, content, "general")
                    elif visibility == "public":
                        orchestrator.memory.update_public_memory(entity_id, content)
                    else:
                        return f"Unknown visibility: {visibility}"
                    
                    return f"Memory added for {entity_id}: {content[:50]}..."
                except Exception as e:
                    return f"Error adding memory: {e}"
            
            async def _arun(self, entity_id: str, content: str, visibility: str = "private") -> str:
                """Async version of _run"""
                return self._run(entity_id, content, visibility)
        
        tool = AddMemoryTool()
        tool._compiler = self
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
                current = current[index] if isinstance(current, list) and 0 <= index < len(current) else None
            else:
                current = current.get(part) if isinstance(current, dict) else None
            
            if current is None:
                break
        
        return current
    
    def _set_value_at_path(self, path: str, value: Any):
        """Set value at JSON pointer path"""
        if not path or path == "":
            self.spec.state = value
            return
        
        parts = path.split(".")
        current = self.spec.state
        
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
