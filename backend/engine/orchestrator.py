"""
Turn orchestrator - manages turn-based gameplay.

This module coordinates the game loop, managing:
- Context building from game state and history
- LLM narrative generation
- State updates and memory management
- Turn history tracking
"""

import json
import random
from typing import Annotated, Any, Dict, List, Optional, Union

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.db.manager import DatabaseManager
from backend.engine.compiler import ScenarioCompiler
from backend.engine.memory import MemoryManager, MemoryScope, MemoryVisibility
from backend.prompts import NARRATOR_SYSTEM, NARRATOR_USER
from backend.providers import create_provider
from backend.schemas import Outcome, ScenarioSpec
from backend.schemas.outcome import RollRequest
from backend.utils.jsonlogic import JSONLogicEvaluator
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _get_message_content_as_string(message: BaseMessage) -> str:
    """
    Get message content as string, handling both string and list formats.

    LangChain messages can have content as either a string or a list of content blocks.
    When content is a list, it typically contains mixed media elements (text, images, etc.).
    This function extracts text content and converts dict elements to strings for analysis.

    Args:
        message: LangChain message object

    Returns:
        Content as string, empty string if None
    """
    content = message.content
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Join list elements that are strings
        return " ".join(str(item) for item in content if isinstance(item, (str, dict)))
    return str(content)


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
    error_recovery_active: Optional[bool]  # Whether error recovery is active
    error_context: Optional[Dict[str, Any]]  # Error context for recovery


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
        self._session_ref: Optional[Dict[str, Any]] = (
            None  # Will be set to access session data
        )

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
            "private_memory_keys": (
                list(self.memory.private_memory.keys())
                if hasattr(self.memory, "private_memory")
                else []
            ),
            "public_memory_size": (
                len(self.memory.public_memory)
                if hasattr(self.memory, "public_memory")
                else 0
            ),
            "session_id": self.memory.session_id,
        }

    def set_session_ref(self, session_ref: Dict[str, Any]):
        """
        Set reference to session data for accessing turn history.

        Args:
            session_ref: Dictionary containing session data including turn_history
        """
        self._session_ref = session_ref

    def _build_graph(self) -> Any:
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

        # Add tool node for tool execution with error handling
        builder.add_node("tools", self._call_tools_with_logging)

        # Add tool result processing node
        builder.add_node("process_tools", self._process_tool_results)

        # Add error handling node
        builder.add_node("handle_errors", self._handle_errors)

        # Add final outcome node for structured response
        builder.add_node("outcome", self._generate_outcome)

        # Add reflection node for post-narrative memory updates
        builder.add_node("reflection", self._perform_reflection)

        # Define the enhanced flow
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tools": "tools", "outcome": "outcome", END: END},
        )
        # After tools, process results with error handling
        builder.add_conditional_edges(
            "tools",
            self._check_for_errors,
            {"process": "process_tools", "error": "handle_errors"},
        )
        builder.add_edge("process_tools", "agent")
        builder.add_edge("handle_errors", "agent")
        builder.add_edge("outcome", "reflection")
        builder.add_edge("reflection", END)

        # Compile with checkpointer
        return builder.compile(checkpointer=self.checkpointer)

    async def _perform_reflection(self, state: AgentState) -> Dict[str, Any]:
        """
        Perform reflection phase after narrative generation.

        This node analyzes the generated outcome and prompts the LLM to:
        - Update character memories based on what happened
        - Record important observations and thoughts
        - Update relationships and world state as needed

        Args:
            state: Current agent state with outcome

        Returns:
            Updated state (may include additional tool calls for memory updates)
        """
        logger.debug("[Reflection] Starting reflection phase")

        messages = state["messages"]
        outcome_message = None

        # Find the most recent outcome message
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                content = msg.content
                if isinstance(content, str):
                    content_lower = content.lower()
                    if "narrative" in content_lower and (
                        "turn" in content_lower or "story" in content_lower
                    ):
                        outcome_message = msg
                        break

        if not outcome_message:
            logger.warning("[Reflection] No outcome message found for reflection")
            return {"messages": messages}

        # Create reflection prompt
        reflection_prompt = self._create_reflection_prompt(state, outcome_message)

        # Add reflection message to conversation
        messages.append(HumanMessage(content=reflection_prompt))

        # Get reflection response (may include tool calls for memory updates)
        reflection_response = await self.provider.chat(
            messages=messages, tools=self.tools
        )

        # Add reflection response to messages
        if reflection_response.tool_calls:
            # Format tool_calls for LangGraph compatibility (same as in _call_agent)
            formatted_tool_calls = []
            for i, tc in enumerate(reflection_response.tool_calls):
                logger.debug(f"[Reflection] Processing tool call {i}: {tc}")

                # Handle OpenAI format with "function" wrapper
                if "function" in tc:
                    function_info = tc.get("function", {})
                    tool_name = function_info.get("name")
                    raw_args = function_info.get("arguments", {})
                    logger.debug(
                        f"[Reflection] OpenAI format - tool: {tool_name}, args: {raw_args}"
                    )
                else:
                    # Direct format
                    tool_name = tc.get("name")
                    raw_args = tc.get("args", {})
                    logger.debug(
                        f"[Reflection] Direct format - tool: {tool_name}, args: {raw_args}"
                    )

                # Parse args if they're a string
                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        logger.warning(
                            f"[Reflection] Failed to parse args as JSON: {raw_args}"
                        )
                        parsed_args = {}
                else:
                    parsed_args = raw_args

                formatted_call = {
                    "name": tool_name,
                    "args": parsed_args,
                    "id": tc.get("id"),
                    "type": "tool_call",  # LangGraph expects "tool_call", not "function"
                }

                logger.debug(f"[Reflection] Formatted tool call {i}: {formatted_call}")
                formatted_tool_calls.append(formatted_call)

            # For reflection with tool calls, minimize content to avoid interfering with outcome selection
            assistant_message = AIMessage(
                content="[Memory updates completed]",  # Minimal marker content
                tool_calls=formatted_tool_calls,
            )
        else:
            # For reflection without tool calls, use minimal content
            assistant_message = AIMessage(content="[No memory updates needed]")

        logger.debug("[Reflection] Reflection phase completed")
        return {"messages": messages + [assistant_message]}

    def _create_reflection_prompt(
        self, state: AgentState, outcome_message: BaseMessage
    ) -> str:
        """
        Create a reflection prompt to analyze the outcome and update memories.

        Args:
            state: Current agent state
            outcome_message: The outcome message to analyze

        Returns:
            Reflection prompt string
        """
        # Extract key information from the outcome
        outcome_content = outcome_message.content or ""

        # Get recent context for reflection
        recent_context = self._build_context_from_state(state)

        return f"""REFLECTION PHASE: Analyze the recent outcome and update memories accordingly.

Recent Outcome:
{outcome_content[:500]}{'...' if len(outcome_content) > 500 else ''}

Current Context:
- Turn: {recent_context.get('turn', 'unknown')}
- Entities: {len(recent_context.get('entities', []))} active
- Location: {recent_context.get('state', {}).get('location', 'unknown')}

Based on this outcome, consider:
1. **Character Memories**: What should NPCs remember about these events?
2. **Relationship Updates**: How did interactions affect relationships?
3. **World State**: What changed in the world that should be remembered?
4. **Important Observations**: What key details emerged that characters should recall?

Use memory tools to record these insights. Focus on:
- NPC thoughts and reactions to events
- Relationship developments (trust, affection, rivalries)
- World changes that affect future decisions
- Key information that might be relevant later

IMPORTANT: Use ONLY tool calls to update memories. Do NOT provide any textual response - only call the add_memory tool for each insight you want to record."""

    def _check_for_errors(self, state: AgentState) -> str:
        """
        Check if recent tool execution had errors requiring special handling.

        Args:
            state: Current agent state

        Returns:
            "error" if errors detected, "process" for normal processing
        """
        messages = state["messages"]

        # Check last few messages for tool errors
        recent_messages = messages[-5:] if len(messages) >= 5 else messages
        tool_messages = [m for m in recent_messages if isinstance(m, ToolMessage)]

        # Count error messages
        error_count = sum(
            1
            for m in tool_messages
            if "error" in _get_message_content_as_string(m).lower()
        )

        if error_count > 0:
            logger.debug(
                f"[ErrorChecker] Detected {error_count} tool errors, routing to error handler"
            )
            return "error"

        logger.debug("[ErrorChecker] No errors detected, routing to normal processing")
        return "process"

    async def _handle_errors(self, state: AgentState) -> Dict[str, Any]:
        """
        Handle tool execution errors with recovery strategies.

        Args:
            state: Current agent state with errors

        Returns:
            Updated state with error recovery information
        """
        logger.debug("[ErrorHandler] Handling tool execution errors")

        messages = state["messages"]
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        error_messages = [
            m
            for m in tool_messages
            if "error" in _get_message_content_as_string(m).lower()
        ]

        # Analyze error patterns
        error_analysis = self._analyze_errors(error_messages)

        # Create recovery message for the agent
        recovery_message = self._create_recovery_message(error_analysis)

        # Update state with recovery context
        current_tool_results = state.get("tool_results", [])
        new_tool_results = current_tool_results + [
            {
                "execution_count": len(current_tool_results) + 1,
                "errors_detected": len(error_messages),
                "error_analysis": error_analysis,
                "recovery_attempted": True,
            }
        ]

        return {
            "messages": [recovery_message],
            "tool_results": new_tool_results,
            "error_recovery_active": True,
        }

    def _analyze_errors(self, error_messages: List[ToolMessage]) -> Dict[str, Any]:
        """
        Analyze error patterns to determine recovery strategy.

        Args:
            error_messages: Messages containing tool errors

        Returns:
            Error analysis results
        """
        if not error_messages:
            return {"error_count": 0, "error_types": [], "severity": "none"}

        error_types = []
        severity_indicators = []

        for msg in error_messages:
            content = _get_message_content_as_string(msg).lower()

            # Categorize error types
            if "not found" in content or "missing" in content:
                error_types.append("missing_resource")
            elif "permission" in content or "forbidden" in content:
                error_types.append("permission")
            elif "syntax" in content or "invalid" in content:
                error_types.append("syntax")
            elif "timeout" in content or "network" in content:
                error_types.append("network")
            else:
                error_types.append("unknown")

            # Assess severity
            if "critical" in content or "fatal" in content:
                severity_indicators.append("high")
            elif "warning" in content:
                severity_indicators.append("low")
            else:
                severity_indicators.append("medium")

        # Determine overall severity
        if "high" in severity_indicators:
            overall_severity = "high"
        elif all(s == "low" for s in severity_indicators):
            overall_severity = "low"
        else:
            overall_severity = "medium"

        return {
            "error_count": len(error_messages),
            "error_types": list(set(error_types)),
            "severity": overall_severity,
            "recoverable": overall_severity != "high",
        }

    def _create_recovery_message(self, error_analysis: Dict[str, Any]) -> HumanMessage:
        """
        Create a recovery message to guide the agent after errors.

        Args:
            error_analysis: Results from error analysis

        Returns:
            Human message with recovery guidance
        """
        error_count = error_analysis.get("error_count", 0)
        error_types = error_analysis.get("error_types", [])
        severity = error_analysis.get("severity", "unknown")
        recoverable = error_analysis.get("recoverable", True)

        if not recoverable:
            content = f"Critical errors detected ({error_count} errors). Please provide a narrative outcome based on current state without further tool usage."
        elif "missing_resource" in error_types:
            content = f"Some resources were not found ({error_count} errors). Try using different parameters or create the missing resources first."
        elif "syntax" in error_types:
            content = f"Syntax errors detected ({error_count} errors). Check your tool parameters and try again with corrected values."
        elif error_count > 2:
            content = f"Multiple tool errors ({error_count} errors). Consider simplifying your approach or proceeding with the narrative based on current state."
        else:
            content = f"Tool error detected ({error_count} errors). You can retry with different parameters or proceed to create the narrative outcome."

        return HumanMessage(content=content)

    async def _process_tool_results(self, state: AgentState) -> Dict[str, Any]:
        """
        Process tool results and update state accordingly.

        This node analyzes tool execution results and updates the
        agent state with insights and processed information.

        Args:
            state: Current agent state with tool results

        Returns:
            Updated state with processed tool information
        """
        logger.debug("[ToolProcessor] Processing tool execution results")

        messages = state["messages"]
        current_tool_results = state.get("tool_results", [])

        # Find recent tool messages
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        recent_tool_messages = (
            tool_messages[-3:] if len(tool_messages) >= 3 else tool_messages
        )

        # Analyze tool execution patterns
        tool_analysis = self._analyze_tool_usage(recent_tool_messages, state)

        # Update tool results in state
        new_tool_results = current_tool_results + [
            {
                "execution_count": len(current_tool_results) + 1,
                "tools_in_batch": len(recent_tool_messages),
                "analysis": tool_analysis,
            }
        ]

        # Check for errors in tool execution
        error_messages = [
            m
            for m in recent_tool_messages
            if "error" in _get_message_content_as_string(m).lower()
        ]
        if error_messages:
            logger.warning(
                f"[ToolProcessor] Detected {len(error_messages)} tool errors"
            )
            # Add error recovery context
            recovery_context = self._create_error_recovery_context(error_messages)
            return {"tool_results": new_tool_results, "error_context": recovery_context}

        return {"tool_results": new_tool_results}

    def _analyze_tool_usage(
        self, tool_messages: List[ToolMessage], state: AgentState
    ) -> Dict[str, Any]:
        """
        Analyze recent tool usage patterns for optimization.

        Args:
            tool_messages: Recent tool execution messages
            state: Current agent state

        Returns:
            Analysis results dictionary
        """
        # Extract tool names and results
        tool_info = []
        for msg in tool_messages:
            content = _get_message_content_as_string(msg)
            tool_info.append(
                {
                    "success": "error" not in content.lower(),
                    "result_length": len(content),
                    "contains_state_change": "state" in content.lower(),
                }
            )

        # Calculate effectiveness metrics
        success_rate = (
            sum(1 for t in tool_info if t["success"]) / len(tool_info)
            if tool_info
            else 0
        )
        avg_result_length = (
            sum(t["result_length"] for t in tool_info) / len(tool_info)
            if tool_info
            else 0
        )
        state_modifications = sum(1 for t in tool_info if t["contains_state_change"])

        return {
            "tool_count": len(tool_messages),
            "success_rate": success_rate,
            "avg_result_length": avg_result_length,
            "state_modifications": state_modifications,
            "effectiveness": (
                "high"
                if success_rate > 0.8
                else "medium" if success_rate > 0.5 else "low"
            ),
        }

    def _create_error_recovery_context(
        self, error_messages: List[ToolMessage]
    ) -> Dict[str, Any]:
        """
        Create context information for error recovery.

        Args:
            error_messages: Tool messages containing errors

        Returns:
            Recovery context dictionary
        """
        error_details = []
        for msg in error_messages:
            error_details.append(
                {
                    "tool_call_id": getattr(msg, "tool_call_id", "unknown"),
                    "error_content": _get_message_content_as_string(msg)[:200],
                }
            )

        return {
            "error_count": len(error_messages),
            "error_details": error_details,
            "recovery_strategy": (
                "retry_with_different_params"
                if len(error_details) == 1
                else "simplify_approach"
            ),
        }

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

        logger.debug(f"[Agent] LLM response content: {response.content}")
        logger.debug(f"[Agent] LLM response tool_calls: {response.tool_calls}")

        # Format tool_calls for LangGraph compatibility
        formatted_tool_calls = []
        if response.tool_calls:
            logger.debug(f"[Agent] Processing {len(response.tool_calls)} tool calls")
            for i, tc in enumerate(response.tool_calls):
                logger.debug(f"[Agent] Processing tool call {i}: {tc}")

                # Handle OpenAI format with "function" wrapper
                if "function" in tc:
                    function_info = tc.get("function", {})
                    tool_name = function_info.get("name")
                    raw_args = function_info.get("arguments", {})
                    logger.debug(
                        f"[Agent] OpenAI format - tool: {tool_name}, args: {raw_args}"
                    )
                else:
                    # Direct format
                    tool_name = tc.get("name")
                    raw_args = tc.get("args", {})
                    logger.debug(
                        f"[Agent] Direct format - tool: {tool_name}, args: {raw_args}"
                    )

                # Parse args if they're a string
                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        logger.warning(
                            f"[Agent] Failed to parse args as JSON: {raw_args}"
                        )
                        parsed_args = {}
                else:
                    parsed_args = raw_args

                formatted_call = {
                    "name": tool_name,
                    "args": parsed_args,
                    "id": tc.get("id"),
                    "type": "tool_call",  # LangGraph expects "tool_call", not "function"
                }

                logger.debug(f"[Agent] Formatted tool call {i}: {formatted_call}")
                formatted_tool_calls.append(formatted_call)

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

    async def _call_tools_with_logging(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute tool calls with detailed logging to debug the error.
        """
        try:
            logger.info("[Tools] Starting tool execution")
            messages = state["messages"]
            last_message = messages[-1]

            logger.debug(f"[Tools] Last message type: {type(last_message).__name__}")
            logger.debug(
                f"[Tools] Has tool_calls attribute: {hasattr(last_message, 'tool_calls')}"
            )

            if hasattr(last_message, "tool_calls"):
                logger.debug(f"[Tools] Tool calls: {last_message.tool_calls}")

            # Use standard ToolNode but with error wrapping
            tool_node = ToolNode(self.tools)
            logger.debug(f"[Tools] Created ToolNode with {len(self.tools)} tools")

            # Call the standard ToolNode
            logger.debug("[Tools] Invoking ToolNode...")
            result = await tool_node.ainvoke(state)
            logger.info(f"[Tools] ToolNode completed successfully")
            logger.debug(f"[Tools] Result: {result}")

            return result

        except Exception as e:
            logger.error(f"[Tools] Tool execution failed: {e}")
            logger.error(f"[Tools] Exception type: {type(e).__name__}")

            import traceback

            logger.error(f"[Tools] Full traceback:")
            for line in traceback.format_exc().splitlines():
                logger.error(f"[Tools] {line}")

            # Return error as tool message
            from langchain_core.messages import ToolMessage

            error_message = ToolMessage(
                content=f"Tool execution error: {str(e)}",
                tool_call_id="error",
                name="error",
            )

            return {
                "messages": [error_message],
                "context": state.get("context", {}),
                "game_state": state.get("game_state", {}),
                "entities": state.get("entities", []),
            }

    def _should_continue(self, state: AgentState) -> str:
        """
        Enhanced conditional routing function with intelligent decisions.

        Args:
            state: Current agent state

        Returns:
            Next node name: "tools", "outcome", or END
        """
        messages = state["messages"]
        last_message = messages[-1]

        logger.debug(f"[Router] Examining last message: {type(last_message).__name__}")
        logger.debug(
            f"[Router] Message content preview: {getattr(last_message, 'content', '')[:100]}..."
        )

        # If the LLM made tool calls, execute tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_names = [tc.get("name", "unknown") for tc in last_message.tool_calls]
            logger.info(f"[Router] Routing to tools: {tool_names}")
            logger.debug(f"[Router] Tool calls detail: {last_message.tool_calls}")
            return "tools"

        # Enhanced routing logic based on context and tool results
        tool_results_count = len(state.get("tool_results", []))
        conversation_summary = state.get("conversation_summary", {})

        # Check if we've used too many tools
        max_rounds = 5
        if tool_results_count >= max_rounds:
            logger.debug(
                f"[Router] Max tool rounds reached ({max_rounds}), routing to outcome"
            )
            return "outcome"

        # Analyze conversation patterns for better routing
        if conversation_summary:
            tools_used = conversation_summary.get("tools_used", [])
            message_count = conversation_summary.get("total_messages", 0)

            # If many tools used but no recent progress, finish
            if len(tools_used) >= 3 and message_count > 10:
                logger.debug(
                    "[Router] Detected extensive tool usage, finalizing outcome"
                )
                return "outcome"

        # Check content for decision indicators
        content = _get_message_content_as_string(last_message)

        # Keywords indicating the agent wants to finish
        finish_keywords = [
            "narrative",
            "story",
            "outcome",
            "conclude",
            "finally",
            "in summary",
        ]
        if any(keyword in content.lower() for keyword in finish_keywords):
            logger.debug("[Router] Detected conclusion keywords, routing to outcome")
            return "outcome"

        # Keywords indicating more analysis needed
        analysis_keywords = ["need to", "should check", "let me", "first", "analyze"]
        if any(keyword in content.lower() for keyword in analysis_keywords):
            logger.debug("[Router] Detected analysis needs, allowing more tool usage")
            # Don't force outcome yet, let agent decide if it wants tools

        # Check game state complexity for routing decisions
        game_state = state.get("game_state", {})
        entities = state.get("entities", [])

        # If game state is simple and few entities, lean toward completion
        if len(entities) <= 2 and len(str(game_state)) < 500:
            logger.debug("[Router] Simple game state detected, routing to outcome")
            return "outcome"

        # Default to outcome for final structured response
        logger.debug("[Router] Default routing to outcome")
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
        logger.debug("[Outcome] Requesting structured JSON response from LLM...")
        final_response = await self.provider.chat(
            messages=messages, json_schema=self._get_outcome_schema()
        )

        logger.debug(
            f"[Outcome] LLM response content length: {len(final_response.content or '')}"
        )
        logger.debug(
            f"[Outcome] LLM response preview: {(final_response.content or '')[:200]}..."
        )

        # Store conversation history in state for persistence
        conversation_summary = self._summarize_conversation(messages)

        # Return the structured response as an AIMessage for proper parsing
        # Use a special prefix to identify this as the outcome message
        outcome_content = f"[OUTCOME_MARKER]{final_response.content or ''}"
        outcome_message = AIMessage(content=outcome_content)

        return {
            "messages": [outcome_message],
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
            "error_recovery_active": False,
            "error_context": None,
        }

        # Configure graph execution with thread ID
        config = {"configurable": {"thread_id": self.session_id}}

        logger.info("[Orchestrator] 🎯 Starting Langgraph agent execution")
        logger.info(
            f"[Orchestrator] 🔨 Available tools: {[t.name for t in self.tools]}"
        )

        try:
            # Execute the graph with detailed logging
            logger.debug("[Orchestrator] Starting graph execution...")
            final_state = await self.graph.ainvoke(initial_state, config)

            # Extract the final response for outcome parsing
            messages = final_state["messages"]
            final_message = None

            # Find the outcome message first, then fall back to last assistant message with content
            logger.debug(f"[Orchestrator] Examining {len(messages)} final messages")

            # First pass: look for messages with outcome marker
            for i, msg in enumerate(reversed(messages)):
                content = _get_message_content_as_string(msg)
                logger.debug(
                    f"[Orchestrator] Message {len(messages)-1-i}: {type(msg).__name__} - content length: {len(content)} - has outcome marker: {content.startswith('[OUTCOME_MARKER]')}"
                )
                if content.startswith("[OUTCOME_MARKER]") and content.strip():
                    # Remove the marker prefix
                    clean_content = content[len("[OUTCOME_MARKER]") :].strip()
                    # Create a temporary message with clean content for parsing
                    final_message = type(msg)(content=clean_content)
                    logger.info(
                        f"[Orchestrator] Selected OUTCOME message: {type(msg).__name__} with {len(clean_content)} chars"
                    )
                    logger.debug(
                        f"[Orchestrator] Outcome message content preview: {clean_content[:200]}..."
                    )
                    break

            # Second pass: fall back to any message with content if no outcome message found
            if not final_message:
                logger.debug(
                    "[Orchestrator] No outcome marker found, falling back to last message with content"
                )
                for i, msg in enumerate(reversed(messages)):
                    if hasattr(msg, "content") and msg.content and msg.content.strip():
                        final_message = msg
                        logger.info(
                            f"[Orchestrator] Selected FALLBACK message: {type(msg).__name__} with {len(msg.content)} chars"
                        )
                        logger.debug(
                            f"[Orchestrator] Fallback message content preview: {msg.content[:200]}..."
                        )
                        break

            if not final_message:
                logger.warning("[Orchestrator] No final message found, using fallback")
                outcome = Outcome(
                    narrative="The story continues...",
                    state_changes=[],
                    visible_dialogue=None,
                    roll_requests=None,
                    hidden_memory_updates=None,
                    emotional_state_updates=None,
                    suggested_actions=None,
                )
            else:
                # Parse outcome from final message
                outcome = self._parse_outcome(final_message.content)

        except Exception as e:
            logger.error(f"[Orchestrator] Langgraph execution failed: {e}")
            logger.error(f"[Orchestrator] Exception type: {type(e).__name__}")
            logger.error(f"[Orchestrator] Exception args: {e.args}")

            # Log the full traceback to understand where the error originates
            import traceback

            logger.error(f"[Orchestrator] Full traceback:")
            for line in traceback.format_exc().splitlines():
                logger.error(f"[Orchestrator] {line}")

            # Fallback to minimal outcome
            outcome = Outcome(
                narrative="The story continues...",
                state_changes=[],
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
                emotional_state_updates=None,
                suggested_actions=None,
            )

        # Apply state changes and update memory (existing logic)
        if outcome.state_changes:
            logger.info(
                f"[Orchestrator] Applying {len(outcome.state_changes)} state changes..."
            )
            self._apply_state_changes(outcome.state_changes)

        # Process memory updates
        if outcome.hidden_memory_updates:
            logger.info(
                f"[Orchestrator] Processing {len(outcome.hidden_memory_updates)} memory updates..."
            )
            self._update_memory(outcome.hidden_memory_updates)

        # Process emotional state updates
        if outcome.emotional_state_updates:
            logger.info(
                f"[Orchestrator] Processing {len(outcome.emotional_state_updates)} emotional state updates..."
            )
            self._update_emotional_states(outcome.emotional_state_updates)

        # Increment turn counter
        self.memory.increment_turn()
        logger.info(f"[Orchestrator] ✅ Turn completed: {self.memory.get_turn_count()}")

        # Periodic memory consolidation (every 10 turns or when memory gets large)
        turn_count = self.memory.get_turn_count()
        memory_stats = self.memory.get_memory_statistics()

        # Trigger consolidation if:
        # 1. Every 10 turns, OR
        # 2. Total memories exceed 200, OR
        # 3. Any entity has more than 30 memories
        should_consolidate = (
            turn_count % 10 == 0
            or memory_stats["total_memories"] > 200
            or any(
                entity["memory_count"] > 30
                for entity in memory_stats.get("largest_entities", [])
            )
        )

        if should_consolidate:
            logger.info(
                f"[Orchestrator] Triggering memory consolidation (turn {turn_count})"
            )
            consolidation_result = self.consolidate_session_memories()
            if consolidation_result["memories_removed"] > 0:
                logger.info(
                    f"[Orchestrator] Consolidated {consolidation_result['memories_removed']} memories"
                )

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
        # Get POV entity's private memory + curated public memory (hybrid approach)
        pov_entity = self._get_pov_entity()

        # Hybrid memory retrieval: provide recent memories + allow LLM to query for more
        private_memory = self._get_recent_memories(
            pov_entity, scope=None, visibility="private", limit=5
        )
        public_memory = self._get_recent_memories(
            pov_entity, scope=None, visibility="public", limit=3
        )

        # Add semantic search capability indicator
        semantic_search_available = (
            self.memory.semantic_search.is_available()
            if hasattr(self.memory, "semantic_search")
            else False
        )

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
            "semantic_search_available": semantic_search_available,
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

            logger.debug(f"[Parse] Original content length: {len(content)}")
            logger.debug(f"[Parse] Content preview (first 300 chars): {content[:300]}")
            logger.debug(f"[Parse] Content preview (last 100 chars): {content[-100:]}")

            # Fix double curly braces ({{ -> {, }} -> })
            if content.startswith("{{") and content.endswith("}}"):
                logger.debug("[Parse] Removing double curly braces from content")
                content = content[1:-1]  # Remove first and last character

            # Check if content is empty or just whitespace
            if not content or not content.strip():
                logger.warning("[Parse] Content is empty or whitespace only")
                raise json.JSONDecodeError("Empty content", "", 0)

            # Try to parse JSON directly
            logger.debug("[Parse] Attempting direct JSON parse...")
            outcome_data = json.loads(content)
            logger.info(
                f"[Parse] Successfully parsed outcome: {list(outcome_data.keys())}"
            )
            return Outcome(**outcome_data)
        except json.JSONDecodeError as e:
            logger.warning(f"[Parse] JSON parsing error: {e}")
            logger.warning(
                f"[Parse] Failed content (first 500 chars): {repr(content[:500])}"
            )

            # Try to extract JSON from response
            logger.debug("[Parse] Attempting JSON extraction with regex...")
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    logger.debug(
                        f"[Parse] Extracted JSON (first 200 chars): {json_str[:200]}"
                    )
                    outcome_data = json.loads(json_str)
                    logger.info(
                        "[Parse] Successfully extracted and parsed JSON from response"
                    )
                    return Outcome(**outcome_data)
                except Exception as e2:
                    logger.error(f"[Parse] JSON extraction failed: {e2}")
                    logger.debug(
                        f"[Parse] Failed extracted content: {repr(json_str[:200])}"
                    )
            else:
                logger.warning("[Parse] No JSON pattern found in content")

            # Fallback to minimal outcome
            logger.warning("[Parse] Falling back to minimal outcome")
            return Outcome(
                narrative="The story continues...",
                state_changes=[],
                visible_dialogue=None,
                roll_requests=None,
                hidden_memory_updates=None,
                emotional_state_updates=None,
                suggested_actions=None,
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
                emotional_state_updates=None,
                suggested_actions=None,
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

    def _update_emotional_states(self, emotional_updates: List[Any]):
        """
        Process emotional state updates from the narrator's Outcome.

        Args:
            emotional_updates: List of emotional state update objects or dicts from Outcome

        Note:
            Processes emotional_state_updates from the narrator's Outcome,
            updating entity emotional states in the memory system.
            Each update should have: entity_id, emotion, intensity, cause, target_entity.
        """
        for update in emotional_updates:
            # Handle both Pydantic objects and dicts
            if hasattr(update, "entity_id"):
                # Pydantic object
                entity_id = update.entity_id
                emotion = update.emotion
                intensity = update.intensity
                cause = getattr(update, "cause", None)
                target_entity = getattr(update, "target_entity", None)
            else:
                # Dict
                entity_id = update.get("entity_id")
                emotion = update.get("emotion")
                intensity = update.get("intensity", 0.0)
                cause = update.get("cause")
                target_entity = update.get("target_entity")

            if not entity_id or not emotion:
                logger.warning(f"Skipping invalid emotional state update: {update}")
                continue

            # Update emotional state in memory system
            self.memory.update_emotional_state(
                entity_id=entity_id,
                emotion=emotion,
                intensity=intensity,
                cause=cause,
                target_entity=target_entity,
            )
            logger.debug(
                f"Updated emotional state for {entity_id}: {emotion} ({intensity})"
            )

    def consolidate_session_memories(self) -> Dict[str, Any]:
        """
        Trigger memory consolidation for the current session.

        This should be called periodically (e.g., every 10-20 turns) to
        prevent memory bloat and improve performance.

        Returns:
            Summary of consolidation actions taken
        """
        logger.info("[Orchestrator] Starting memory consolidation...")

        # Consolidate memories using intelligent thresholds
        max_memories = 50  # Keep top 50 memories per entity per scope
        threshold = max(
            10, self.memory.get_turn_count() // 5
        )  # Consolidate after 10, then every 5 turns

        consolidation_result = self.memory.consolidate_memories(
            max_memories_per_entity=max_memories, consolidation_threshold=threshold
        )

        # Save consolidated memory to database
        self.memory.save_to_database()

        logger.info(
            f"[Orchestrator] Memory consolidation completed: {consolidation_result}"
        )
        return consolidation_result

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics for monitoring and debugging.

        Returns:
            Dictionary with memory system statistics
        """
        return self.memory.get_memory_statistics()

    def _get_pov_entity(self) -> str:
        """
        Get the point-of-view entity ID for the current session.

        Returns:
            Entity ID string for the player character

        Note:
            Enhanced to detect player character based on:
            - POV marker in state
            - Player character entity created by initializer
            - Player type entities
            - Legacy "player" entity
        """
        # Check if there's a POV marker in state
        if hasattr(self.spec, "state") and isinstance(self.spec.state, dict):
            pov = self.spec.state.get("pov_entity")
            if pov:
                return pov

        # Check if there's a player entity in entities list
        if self.spec.entities:
            # First, look for player_character (created by initializer with user's name)
            for entity in self.spec.entities:
                if entity.get("id") == "player_character":
                    return entity.get("id", "player_character")

            # Then look for explicit player type entities
            for entity in self.spec.entities:
                if entity.get("type") == "player":
                    return entity.get("id", "player")

            # Finally, look for legacy "player" id
            for entity in self.spec.entities:
                if entity.get("id") == "player":
                    return entity.get("id", "player")

        # Default to "player"
        return "player"

    def _get_available_actions(self) -> List[str]:
        """
        Get list of available action IDs for the current state.

        Returns:
            List of action ID strings filtered by preconditions

        Filters actions based on:
        - Preconditions against current state
        - Location/context restrictions
        - Entity capabilities
        """
        available = []

        for action in self.spec.actions:
            if self._check_preconditions(action.preconditions, self.spec.state):
                available.append(action.id)

        logger.debug(f"Available actions: {available}")
        return available

    def _check_preconditions(
        self, preconditions: Dict[str, Any], state: Dict[str, Any]
    ) -> bool:
        """
        Check if action preconditions are met against current state.

        Args:
            preconditions: JSONLogic expression for preconditions
            state: Current game state

        Returns:
            True if preconditions are met, False otherwise
        """
        if not preconditions:
            # No preconditions means action is always available
            return True

        try:
            evaluator = JSONLogicEvaluator()
            return evaluator.evaluate_condition(preconditions, state)
        except Exception as e:
            logger.warning(f"Precondition evaluation failed for {preconditions}: {e}")
            # On evaluation error, default to available to avoid blocking gameplay
            return True

    def _resolve_roll_request(self, roll_request: RollRequest) -> Dict[str, Any]:
        """
        Resolve a roll request with d20 mechanics and character stats.

        Args:
            roll_request: The roll request from the LLM

        Returns:
            Dictionary with roll result, success/failure, and narrative context
        """
        # Get character stats if target is specified
        character_stats = self._get_character_stats(roll_request.target)

        # Roll d20
        roll = random.randint(1, 20)

        # Add relevant modifiers based on roll type
        modifier = self._get_roll_modifier(roll_request.kind, character_stats)

        total = roll + modifier

        # Determine success/failure
        success = total >= roll_request.difficulty
        margin = abs(total - roll_request.difficulty)

        return {
            "roll": roll,
            "modifier": modifier,
            "total": total,
            "success": success,
            "margin": margin,
            "difficulty": roll_request.difficulty,
            "character_stats": character_stats,
            "narrative_context": self._generate_roll_narrative(
                roll_request, roll, total, success
            ),
        }

    def _get_character_stats(self, entity_id: Optional[str]) -> Dict[str, Any]:
        """Get character stats for roll modifiers"""
        if not entity_id:
            return {"modifier": 0}

        # Look for character in entities
        for entity in self.spec.entities:
            if entity.get("id") == entity_id:
                stats = entity.get("stats", {})
                return {
                    "modifier": stats.get("persuasion_modifier", 0),
                    "strength": stats.get("strength", 10),
                    "dexterity": stats.get("dexterity", 10),
                    "intelligence": stats.get("intelligence", 10),
                    "charisma": stats.get("charisma", 10),
                }

        return {"modifier": 0}

    def _get_roll_modifier(
        self, roll_kind: str, character_stats: Dict[str, Any]
    ) -> int:
        """Get appropriate modifier based on roll type and character stats"""
        base_modifier = character_stats.get("modifier", 0)

        # Apply specific modifiers based on roll type
        if roll_kind in ["persuasion", "diplomacy", "charm"]:
            return base_modifier + (character_stats.get("charisma", 10) - 10) // 2
        elif roll_kind in ["athletics", "climb", "swim"]:
            return base_modifier + (character_stats.get("strength", 10) - 10) // 2
        elif roll_kind in ["stealth", "sleight_of_hand", "acrobatics"]:
            return base_modifier + (character_stats.get("dexterity", 10) - 10) // 2
        elif roll_kind in ["investigation", "arcana", "history", "nature", "religion"]:
            return base_modifier + (character_stats.get("intelligence", 10) - 10) // 2
        else:
            # Default modifier for other roll types
            return base_modifier

    def _generate_roll_narrative(
        self, roll_request: RollRequest, roll: int, total: int, success: bool
    ) -> str:
        """Generate narrative context for roll results"""
        if success:
            if total >= roll_request.difficulty + 5:
                return f"You succeed spectacularly! (rolled {roll} + {total - roll} modifier = {total} vs DC {roll_request.difficulty})"
            else:
                return f"You succeed. (rolled {roll} + {total - roll} modifier = {total} vs DC {roll_request.difficulty})"
        else:
            margin = roll_request.difficulty - total
            if margin >= 5:
                return f"You fail catastrophically! (rolled {roll} + {total - roll} modifier = {total} vs DC {roll_request.difficulty})"
            else:
                return f"You fail. (rolled {roll} + {total - roll} modifier = {total} vs DC {roll_request.difficulty})"

    def _get_recent_memories(
        self,
        entity_id: str,
        scope: Optional[MemoryScope] = None,
        visibility: Optional[MemoryVisibility] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories for hybrid retrieval approach.

        This method provides a curated selection of recent memories
        rather than all memories, allowing the LLM to query for more
        specific information using semantic search if needed.

        Args:
            entity_id: Entity to get memories for
            scope: Memory scope filter (optional)
            visibility: Memory visibility filter (optional)
            limit: Maximum number of memories to return

        Returns:
            List of recent memories, sorted by importance and recency
        """
        # Use the enhanced memory system to get scoped memories
        memories = self.memory.get_scoped_memory(
            entity_id=entity_id, scope=scope, visibility=visibility, limit=limit
        )

        # Format for context (simplified format)
        formatted_memories = []
        for memory in memories:
            formatted_memories.append(
                {
                    "content": memory["content"],
                    "scope": memory["scope"],
                    "turn": memory["turn"],
                    "importance": memory.get("importance", 5),
                }
            )

        return formatted_memories

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
