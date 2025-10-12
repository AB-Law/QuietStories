"""
Turn orchestrator - manages turn-based gameplay.

This module coordinates the game loop, managing:
- Context building from game state and history
- LLM narrative generation
- State updates and memory management
- Turn history tracking
"""

import json
from typing import Annotated, Any, Dict, List, Optional

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.db.manager import DatabaseManager
from backend.engine.compiler import ScenarioCompiler
from backend.engine.memory import MemoryManager
from backend.prompts import NARRATOR_SYSTEM, NARRATOR_USER
from backend.providers import create_provider
from backend.schemas import Outcome, ScenarioSpec
from backend.utils.jsonlogic import JSONLogicEvaluator
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    """
    Agent state schema for the Langgraph StateGraph.

    This combines messages, game state, and tool results for
    comprehensive agent state management across turns.
    """

    messages: Annotated[
        List[BaseMessage], add_messages
    ]  # Conversation history with reducer
    game_state: Dict[str, Any]  # Current scenario state
    entities: List[Dict[str, Any]]  # Current entity list
    session_id: str  # Session identifier
    turn_count: int  # Current turn number
    tool_results: List[Dict[str, Any]]  # Results from tool executions
    context: Optional[Dict[str, Any]]  # Additional context data
    user_input: Optional[str]  # Current user input
    conversation_summary: Optional[Dict[str, Any]]  # Summary for persistence
    memory_state: Optional[Dict[str, Any]]  # Memory manager state snapshot


class TurnOrchestrator:
    """
    Orchestrates turn-based gameplay with LLM integration.

    This class manages the game loop, building context from game state,
    turn history, and memory to generate coherent narratives. It implements
    smart context selection to keep LLM prompts focused and efficient.

    Attributes:
        spec: The scenario specification defining the game rules
        session_id: Unique identifier for this game session
        provider: LLM provider for narrative generation
        compiler: Compiler for scenario actions
        memory: Manager for entity memories
        tools: Compiled scenario actions (not used for narrator)
        _session_ref: Reference to fetch turn history
    """

    def __init__(self, spec: ScenarioSpec, session_id: str, db_manager=None):
        """
        Initialize the turn orchestrator.

        Args:
            spec: Scenario specification defining game rules
            session_id: Unique session identifier
            db_manager: Database manager for persistence (optional)
        """
        self.spec = spec
        self.session_id = session_id
        self.db_manager = db_manager
        self.provider = create_provider()
        self.compiler = ScenarioCompiler(spec)
        self.compiler._orchestrator = self  # type: ignore # Give compiler access to orchestrator

        # Load memory from database if available
        private_memory = {}
        public_memory = {}
        turn_count = 0
        if db_manager:
            session_data = db_manager.get_session(session_id)
            if session_data:
                private_memory = session_data.get("private_memory", {})
                public_memory = session_data.get("public_memory", {})
                turn_count = session_data.get("turn", 0)

        self.memory = MemoryManager(
            session_id, db_manager, private_memory, public_memory, turn_count
        )
        self.tools = self.compiler.get_tools()
        self._session_ref: Optional[
            Dict[str, Any]
        ] = None  # Will be set to access session data

        # Initialize Langgraph components
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _get_memory_state_snapshot(self) -> Dict[str, Any]:
        """
        Create a snapshot of the current memory manager state for persistence.

        Returns:
            Dictionary containing memory state information
        """
        return {
            "turn_count": self.memory.get_turn_count(),
            "private_memory_keys": list(self.memory.private_memory.keys())
            if hasattr(self.memory, "private_memory")
            else [],
            "public_memory_size": len(self.memory.public_memory)
            if hasattr(self.memory, "public_memory")
            else 0,
            "session_id": self.memory.session_id,
        }

    def set_session_ref(self, session_ref: Dict[str, Any]):
        """
        Set reference to session data for accessing turn history.

        Args:
            session_ref: Dictionary containing session data including turn_history
        """
        self._session_ref = session_ref

    def _build_graph(self) -> StateGraph:
        """
        Build the Langgraph StateGraph for agent orchestration.

        Creates a graph with agent and tool nodes, replacing the
        simple while loop with sophisticated state management.

        Returns:
            Compiled StateGraph ready for execution
        """
        # Create the StateGraph
        builder = StateGraph(AgentState)

        # Add agent node for LLM calls
        builder.add_node("agent", self._call_agent)

        # Add tool node for tool execution
        tool_node = ToolNode(self.tools)
        builder.add_node("tools", tool_node)

        # Add final outcome node for structured response
        builder.add_node("outcome", self._generate_outcome)

        # Define the flow
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tools": "tools", "outcome": "outcome", END: END},
        )
        builder.add_edge("tools", "agent")
        builder.add_edge("outcome", END)

        # Compile with checkpointer
        return builder.compile(checkpointer=self.checkpointer)

    async def _call_agent(self, state: AgentState) -> Dict[str, Any]:
        """
        Agent node: Call LLM to decide on tool usage or final response.

        Args:
            state: Current agent state

        Returns:
            Updated state with new message
        """
        logger.debug("[Agent] Calling LLM for decision making")

        # Update game state in messages if it has changed
        current_game_state = state["game_state"]
        current_entities = state["entities"]

        # Build fresh context with current state
        fresh_context = self._build_context_from_state(state)

        # Get the latest messages from state
        messages = state["messages"]

        # Call LLM with tools
        response = await self.provider.chat(messages=messages, tools=self.tools)

        # Format tool_calls for LangChain compatibility
        formatted_tool_calls = []
        if response.tool_calls:
            for tc in response.tool_calls:
                raw_args = tc.get("function", {}).get("arguments", {})
                # Parse args if they're a string
                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        parsed_args = {}
                else:
                    parsed_args = raw_args

                formatted_tool_calls.append(
                    {
                        "name": tc.get("function", {}).get("name"),
                        "args": parsed_args,
                        "id": tc.get("id"),
                        "type": tc.get("type", "function"),
                    }
                )

        # Create AIMessage
        if formatted_tool_calls:
            assistant_message = AIMessage(
                content=response.content or "", tool_calls=formatted_tool_calls
            )
        else:
            assistant_message = AIMessage(content=response.content or "")

        # Update state with fresh context
        return {
            "messages": [assistant_message],
            "context": fresh_context,
            "game_state": self.spec.state,  # Keep state synchronized
            "entities": self.spec.entities,
        }

    def _should_continue(self, state: AgentState) -> str:
        """
        Conditional routing function to decide next step.

        Args:
            state: Current agent state

        Returns:
            Next node name: "tools", "outcome", or END
        """
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM made tool calls, execute tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.debug(
                f"[Router] Routing to tools: {len(last_message.tool_calls)} tool calls"
            )
            return "tools"

        # Check if we've exceeded max rounds (simple counter from tool_results)
        tool_results_count = len(state.get("tool_results", []))
        max_rounds = 5

        if tool_results_count >= max_rounds:
            logger.debug(
                f"[Router] Max rounds reached ({max_rounds}), routing to outcome"
            )
            return "outcome"

        # Check if response looks like final narrative (simple heuristic)
        content = last_message.content or ""
        if any(
            keyword in content.lower()
            for keyword in ["narrative", "story", "continues", "outcome"]
        ):
            logger.debug("[Router] Detected narrative content, routing to outcome")
            return "outcome"

        # Default to outcome for final structured response
        logger.debug("[Router] Routing to outcome for final response")
        return "outcome"

    async def _generate_outcome(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate final structured outcome from agent reasoning.

        Args:
            state: Current agent state

        Returns:
            Updated state with structured outcome
        """
        logger.debug("[Outcome] Generating structured outcome")

        # Add request for structured outcome
        messages = state["messages"]
        messages.append(
            HumanMessage(
                content="Now provide the final narrative outcome as structured JSON with the Outcome schema."
            )
        )

        # Get structured response
        final_response = await self.provider.chat(
            messages=messages, json_schema=self._get_outcome_schema()
        )

        # Store conversation history in state for persistence
        conversation_summary = self._summarize_conversation(messages)

        return {
            "messages": [
                HumanMessage(content=f"Generated outcome: {final_response.content}")
            ],
            "conversation_summary": conversation_summary,
        }

    def _summarize_conversation(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        Create a summary of the conversation for state persistence.

        Args:
            messages: List of messages from the conversation

        Returns:
            Dictionary containing conversation summary
        """
        # Count different message types
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        # Extract tool usage patterns
        tools_used = []
        for ai_msg in ai_messages:
            if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)

        return {
            "total_messages": len(messages),
            "human_messages": len(human_messages),
            "ai_messages": len(ai_messages),
            "tool_messages": len(tool_messages),
            "tools_used": tools_used,
            "last_user_input": human_messages[-1].content if human_messages else None,
            "conversation_length": sum(
                len(m.content or "") for m in messages if hasattr(m, "content")
            ),
        }

    async def process_turn(self, user_input: Optional[str] = None) -> Outcome:
        """
        Process a single turn using Langgraph StateGraph.

        This method replaces the old while-loop implementation with
        a sophisticated stateful agent workflow using Langgraph.

        Args:
            user_input: Optional player action description

        Returns:
            Outcome object containing narrative and state changes
        """
        logger.info(
            f"[Orchestrator] Processing turn {self.memory.get_turn_count() + 1} with Langgraph StateGraph"
        )

        # Build context for the LLM
        context = self._build_context()

        # Initialize agent state
        initial_state: AgentState = {
            "messages": [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=self._get_user_prompt(context, user_input)),
            ],
            "game_state": self.spec.state,
            "entities": self.spec.entities,
            "session_id": self.session_id,
            "turn_count": self.memory.get_turn_count(),
            "tool_results": [],
            "context": context,
            "user_input": user_input,
            "conversation_summary": None,
            "memory_state": self._get_memory_state_snapshot(),
        }

        # Configure graph execution with thread ID
        config = {"configurable": {"thread_id": self.session_id}}

        logger.info("[Orchestrator] 🎯 Starting Langgraph agent execution")
        logger.info(f"[Orchestrator] 🔨 Available tools: {[t.name for t in self.tools]}")

        try:
            # Execute the graph
            final_state = await self.graph.ainvoke(initial_state, config)

            # Extract the final response for outcome parsing
            messages = final_state["messages"]
            final_message = None

            # Find the last assistant message with content
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content and msg.content.strip():
                    final_message = msg
                    break

            if not final_message:
                logger.warning("[Orchestrator] No final message found, using fallback")
                outcome = Outcome(
                    narrative="The story continues...",
                    state_changes=[],
                    visible_dialogue=None,
                    roll_requests=None,
                    hidden_memory_updates=None,
                )
            else:
                # Parse outcome from final message
                outcome = self._parse_outcome(final_message.content)

        except Exception as e:
            logger.error(f"[Orchestrator] Langgraph execution failed: {e}")
            # Fallback to minimal outcome
            outcome = Outcome(
                narrative="The story continues...",
                state_changes=[],
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
            )

        # Apply state changes and update memory (existing logic)
        if outcome.state_changes:
            logger.info(
                f"[Orchestrator] Applying {len(outcome.state_changes)} state changes..."
            )
            self._apply_state_changes(outcome.state_changes)

        # Increment turn counter
        self.memory.increment_turn()
        logger.info(f"[Orchestrator] ✅ Turn completed: {self.memory.get_turn_count()}")

        # Save memory to database
        self.memory.save_to_database()

        return outcome

    def _build_context_from_state(self, state: AgentState) -> Dict[str, Any]:
        """
        Build context from current agent state for enhanced state management.

        This method creates fresh context incorporating the current state
        from the Langgraph AgentState, ensuring consistency across tool calls.

        Args:
            state: Current agent state from Langgraph

        Returns:
            Dictionary containing updated context information
        """
        # Use current state from agent state
        current_game_state = state["game_state"]
        current_entities = state["entities"]
        current_turn_count = state["turn_count"]

        # Get POV entity's private memory + all public memory
        pov_entity = self._get_pov_entity()
        private_memory = self.memory.get_private_memory(pov_entity)
        public_memory = self.memory.get_public_memory()

        # Get turn history for context
        recent_turns = self._get_recent_turns(3)  # Last 3 turns verbatim
        history_summary = self._get_history_summary()  # Summarized older turns

        # Get world background if available
        world_background = None
        if self._session_ref and "world_background" in self._session_ref:
            world_background = self._session_ref["world_background"]

        return {
            "state": current_game_state,
            "entities": current_entities,
            "recent_turns": recent_turns,
            "history_summary": history_summary,
            "private_memory": private_memory,
            "public_memory": public_memory,
            "turn": current_turn_count,
            "available_actions": self._get_available_actions(),
            "world_background": world_background,
        }

    def _build_context(self) -> Dict[str, Any]:
        """
        Build comprehensive context for the LLM narrator.

        This method assembles all relevant information for generating
        the next turn's narrative, using smart context selection to
        keep prompts focused and efficient.

        Returns:
            Dictionary containing:
                - state: Current game state
                - entities: Current entity list
                - recent_turns: Last 3 turns verbatim
                - history_summary: Summary of older turns
                - private_memory: POV entity's private memories
                - public_memory: All public memories
                - turn: Current turn number
                - available_actions: Actions available to player
                - world_background: World setting (if available)

        Note:
            Context selection prioritizes recent information and
            summarizes older content to fit within LLM context limits.
        """
        # Get POV entity's private memory + all public memory
        pov_entity = self._get_pov_entity()
        private_memory = self.memory.get_private_memory(pov_entity)
        public_memory = self.memory.get_public_memory()

        # Get turn history for context
        recent_turns = self._get_recent_turns(3)  # Last 3 turns verbatim
        history_summary = self._get_history_summary()  # Summarized older turns

        # Get world background if available
        world_background = None
        if self._session_ref and "world_background" in self._session_ref:
            world_background = self._session_ref["world_background"]

        return {
            "state": self.spec.state,
            "entities": self.spec.entities,
            "recent_turns": recent_turns,
            "history_summary": history_summary,
            "private_memory": private_memory,
            "public_memory": public_memory,
            "turn": self.memory.get_turn_count(),
            "available_actions": self._get_available_actions(),
            "world_background": world_background,
        }

    def _get_system_prompt(self) -> str:
        """Get system prompt for the narrator"""
        return NARRATOR_SYSTEM

    def _get_user_prompt(
        self, context: Dict[str, Any], user_input: Optional[str] = None
    ) -> str:
        """
        Generate user prompt with full context for narrator.

        Args:
            context: Context dictionary from _build_context()
            user_input: Optional player action description

        Returns:
            Formatted prompt string with all relevant context

        Note:
            This method formats context into a narrative-friendly structure,
            prioritizing recent events and current state information.
        """
        state_summary = json.dumps(context["state"], indent=2)

        # Format recent turns
        recent_turns_text = ""
        if context.get("recent_turns"):
            turns_list = []
            for turn in context["recent_turns"]:
                turns_list.append(
                    f"Turn {turn['turn']}: {turn.get('user_action', 'Continue')}"
                )
                turns_list.append(f"  Narrative: {turn['narrative'][:200]}...")
            recent_turns_text = "\n".join(turns_list)
        else:
            recent_turns_text = "No previous turns"

        # Format history summary
        history_text = context.get(
            "history_summary", "This is the beginning of the story"
        )

        # Format entities
        entities_text = ""
        if context.get("entities"):
            entities_list = [
                f"- {e.get('id', 'unknown')}: {e.get('type', 'entity')}"
                for e in context["entities"][:10]
            ]
            entities_text = "\n".join(entities_list)
        else:
            entities_text = "No entities yet"

        # Format world background
        world_text = context.get("world_background", "No world background available")

        # Build complete prompt
        return NARRATOR_USER.format(
            state_summary=state_summary,
            world_background=world_text[:500] if world_text else "Unknown",
            recent_turns=recent_turns_text,
            history_summary=history_text,
            entities_summary=entities_text,
            action=user_input or "Continue the story",
        )

    def _get_outcome_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for outcome validation.

        Returns:
            JSON schema generated from Pydantic Outcome model
        """
        # Use Pydantic's generated schema for accuracy
        return Outcome.model_json_schema()

    def _get_recent_turns(self, n: int = 3) -> List[Dict[str, Any]]:
        """
        Fetch the last N turns from session history.

        Args:
            n: Number of recent turns to retrieve (default: 3)

        Returns:
            List of turn records, most recent last. Empty list if no history.

        Note:
            This method fetches from the session stored in _session_ref.
            If _session_ref is not set, returns empty list.
        """
        if not self._session_ref or "turn_history" not in self._session_ref:
            return []

        turn_history = self._session_ref.get("turn_history", [])
        if not turn_history:
            return []

        # Return last N turns
        recent = turn_history[-n:] if len(turn_history) >= n else turn_history
        logger.debug(f"Retrieved {len(recent)} recent turns")
        return recent

    def _get_history_summary(self) -> str:
        """
        Get a summary of older turns (beyond the recent 3).

        Returns:
            A summary string of historical events, or empty string if not enough history

        Note:
            This method summarizes turns in batches of 5 to keep context manageable.
            Only summarizes turns older than the last 3 (handled by _get_recent_turns).
        """
        if not self._session_ref or "turn_history" not in self._session_ref:
            return ""

        turn_history = self._session_ref.get("turn_history", [])

        # Only summarize if we have more than 3 turns
        if len(turn_history) <= 3:
            return ""

        # Get turns to summarize (all except last 3)
        older_turns = turn_history[:-3]

        if not older_turns:
            return ""

        # Simple summarization: extract key events every 5 turns
        summary_points = []
        for i in range(0, len(older_turns), 5):
            batch = older_turns[i : i + 5]
            # Extract narrative highlights from batch
            highlights = [
                f"Turn {turn['turn']}: {turn.get('user_action', 'continued')}"
                for turn in batch[:2]  # Just first 2 of each batch
            ]
            summary_points.extend(highlights)

        if summary_points:
            summary = "Earlier events: " + "; ".join(
                summary_points[:10]
            )  # Limit to 10 points
            logger.debug(f"Generated history summary with {len(summary_points)} points")
            return summary

        return ""

    async def _summarize_turns(self, turns: List[Dict[str, Any]]) -> str:
        """
        Use LLM to summarize a batch of turns.

        Args:
            turns: List of turn records to summarize

        Returns:
            A concise summary paragraph

        Note:
            This method is currently not used (simple summarization in _get_history_summary
            is sufficient). Can be activated for more sophisticated summarization if needed.
        """
        if not turns:
            return ""

        # Build summary request
        turns_text = []
        for turn in turns:
            turns_text.append(
                f"Turn {turn['turn']}: {turn.get('user_action', 'Continue')}"
            )
            turns_text.append(f"Result: {turn['narrative'][:150]}...")

        prompt = f"""Summarize these game turns into 2-3 concise sentences capturing key events:

{chr(10).join(turns_text)}

Summary:"""

        messages = [
            SystemMessage(
                content="You are a concise summarizer. Create brief event summaries."
            ),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.provider.chat(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Turn summarization failed: {e}")
            return f"Events during turns {turns[0]['turn']}-{turns[-1]['turn']}"

    def _parse_outcome(self, content: str) -> Outcome:
        """Parse and validate outcome from LLM response"""

        import json
        import logging
        import re

        logger = logging.getLogger(__name__)

        try:
            # Clean up content - remove double curly braces if present
            content = content.strip()

            # Fix double curly braces ({{ -> {, }} -> })
            if content.startswith("{{") and content.endswith("}}"):
                logger.debug("Removing double curly braces from content")
                content = content[1:-1]  # Remove first and last character

            # Try to parse JSON directly
            outcome_data = json.loads(content)
            logger.debug(f"Successfully parsed outcome: {list(outcome_data.keys())}")
            return Outcome(**outcome_data)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
            logger.debug(f"Content preview: {content[:200]}")
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    outcome_data = json.loads(json_str)
                    logger.info("Successfully extracted and parsed JSON from response")
                    return Outcome(**outcome_data)
                except Exception as e2:
                    logger.error(f"JSON extraction failed: {e2}")
            # Fallback to minimal outcome
            logger.warning("Falling back to minimal outcome")
            return Outcome(
                narrative="The story continues...",
                state_changes=[],
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
            )
        except Exception as e:
            logger.error(f"Outcome parsing error: {e}", exc_info=True)
            # Fallback to minimal outcome
            return Outcome(
                narrative="The story continues...",
                state_changes=[],
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
            )

    def _apply_state_changes(self, state_changes: List[Any]):
        """
        Apply state changes to the scenario state.

        Args:
            state_changes: List of StateChange objects or dicts

        Note:
            Handles both Pydantic StateChange objects and plain dicts
            for flexibility. Updates self.spec.state in place.
        """
        for change in state_changes:
            try:
                evaluator = JSONLogicEvaluator()

                # Handle both StateChange objects and dicts
                if hasattr(change, "op"):
                    # Pydantic object
                    op = change.op
                    path = change.path if hasattr(change, "path") else ""
                    value = change.value if hasattr(change, "value") else None
                else:
                    # Dict
                    op = change.get("op")
                    path = change.get("path", "")
                    value = change.get("value")

                if op == "set":
                    self._set_value_at_path(path, value)
                elif op == "inc":
                    current_value = self._get_value_at_path(path)
                    self._set_value_at_path(path, current_value + value)
                elif op == "dec":
                    current_value = self._get_value_at_path(path)
                    self._set_value_at_path(path, current_value - value)
                elif op == "mul":
                    current_value = self._get_value_at_path(path)
                    self._set_value_at_path(path, current_value * value)
                elif op == "patch":
                    current_value = self._get_value_at_path(path)
                    if isinstance(current_value, dict) and isinstance(value, dict):
                        current_value.update(value)
                        self._set_value_at_path(path, current_value)
                elif op == "push":
                    current_value = self._get_value_at_path(path)
                    if isinstance(current_value, list):
                        current_value.append(value)
                        self._set_value_at_path(path, current_value)

                        # Detect entity creation
                        if "entities" in path or "entity" in path:
                            entity_id = (
                                value.get("id", "unknown")
                                if isinstance(value, dict)
                                else "unknown"
                            )
                            logger.info(f"New entity created: {entity_id}")
                            # Also update spec.entities if it's the main entities list
                            if path.endswith("entities") and isinstance(value, dict):
                                self.spec.entities.append(value)
                elif op == "pop":
                    current_value = self._get_value_at_path(path)
                    if isinstance(current_value, list) and len(current_value) > 0:
                        current_value.pop()
                        self._set_value_at_path(path, current_value)
                elif op == "addlog":
                    # Add to log list
                    log_path = path if path else "state.log"
                    current_log = self._get_value_at_path(log_path)
                    if isinstance(current_log, list):
                        current_log.append(value)
                        self._set_value_at_path(log_path, current_log)
                    else:
                        self._set_value_at_path(log_path, [value])

            except Exception as e:
                # Log error but continue with other changes
                print(f"Error applying state change {change}: {e}")

    def _get_value_at_path(self, path: str) -> Any:
        """Get value at JSON pointer path"""
        if not path or path == "":
            return self.spec.state

        # Simple path resolution - in production, use proper JSON pointer library
        parts = path.split(".")
        current: Any = self.spec.state

        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                # Array access
                index = int(part[1:-1])
                current = current[index]
            else:
                current = current.get(part, {})

        return current

    def _set_value_at_path(self, path: str, value: Any):
        """Set value at JSON pointer path"""
        if not path or path == "":
            self.spec.state = value
            return

        # Simple path resolution - in production, use proper JSON pointer library
        parts = path.split(".")
        current: Any = self.spec.state

        for i, part in enumerate(parts[:-1]):
            if part.startswith("[") and part.endswith("]"):
                # Array access
                index = int(part[1:-1])
                current = current[index]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Set the final value
        final_part = parts[-1]
        if final_part.startswith("[") and final_part.endswith("]"):
            index = int(final_part[1:-1])
            current[index] = value
        else:
            current[final_part] = value

    def _update_memory(self, memory_updates: List[Any]):
        """
        Update entity memories from hidden memory updates.

        Args:
            memory_updates: List of memory update objects or dicts from Outcome

        Note:
            Processes hidden_memory_updates from the narrator's Outcome,
            routing them to private or public memory based on visibility.
            Each update should have: target_id, content, scope, visibility.
        """
        for update in memory_updates:
            # Handle both Pydantic objects and dicts
            if hasattr(update, "target_id"):
                # Pydantic object
                target_id = update.target_id
                content = update.content
                scope = getattr(update, "scope", "general")
                visibility = getattr(update, "visibility", "private")
            else:
                # Dict
                target_id = update.get("target_id")
                content = update.get("content")
                scope = update.get("scope", "general")
                visibility = update.get("visibility", "private")

            if not target_id or not content:
                logger.warning(f"Skipping invalid memory update: {update}")
                continue

            # Route to appropriate memory based on visibility
            if visibility == "private":
                self.memory.update_private_memory(target_id, content, scope)
                logger.debug(f"Updated private memory for {target_id}")
            elif visibility == "public":
                self.memory.update_public_memory(target_id, content)
                logger.debug(f"Updated public memory for {target_id}")
            else:
                logger.warning(
                    f"Unknown visibility '{visibility}', treating as private"
                )
                self.memory.update_private_memory(target_id, content, scope)

    def _get_pov_entity(self) -> str:
        """
        Get the point-of-view entity ID for the current session.

        Returns:
            Entity ID string (currently defaults to "player")

        Note:
            Current implementation is simplified. In production, this could:
            - Read from session state
            - Support multiple player entities
            - Handle entity switching mid-game
            - Detect from entity list

        TODO: Implement proper POV detection from session/state
        """
        # Check if there's a POV marker in state
        if hasattr(self.spec, "state") and isinstance(self.spec.state, dict):
            pov = self.spec.state.get("pov_entity")
            if pov:
                return pov

        # Check if there's a player entity in entities list
        if self.spec.entities:
            for entity in self.spec.entities:
                if entity.get("type") == "player" or entity.get("id") == "player":
                    return entity.get("id", "player")

        # Default to "player"
        return "player"

    def _get_available_actions(self) -> List[str]:
        """
        Get list of available action IDs for the current state.

        Returns:
            List of action ID strings

        Note:
            Current implementation returns all actions. In production,
            this should filter by:
            - Preconditions against current state
            - Location/context restrictions
            - Entity capabilities

        TODO: Implement precondition checking
        """
        # TODO: Filter actions by preconditions
        # For now, return all action IDs
        action_ids = [action.id for action in self.spec.actions]

        # Future: check preconditions
        # available = []
        # for action in self.spec.actions:
        #     if self._check_preconditions(action.preconditions, self.spec.state):
        #         available.append(action.id)
        # return available

        return action_ids

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool

        Returns:
            String result of tool execution

        Raises:
            ValueError: If tool name is not recognized
        """
        logger.debug(f"[Orchestrator] Executing tool {tool_name} with args: {args}")

        # Find the tool by name
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        try:
            # Execute the tool directly by calling _arun with unpacked arguments
            result = await tool._arun(**args)
            logger.debug(f"[Orchestrator] Tool {tool_name} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"[Orchestrator] Tool {tool_name} execution error: {e}")
            raise
