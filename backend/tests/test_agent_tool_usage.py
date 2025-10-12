"""
Integration tests for Langgraph agent tool usage patterns.

This module tests the enhanced agent tool orchestration features
including routing, error handling, and tool result processing.
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage

from backend.engine.orchestrator import AgentState, TurnOrchestrator
from backend.schemas.outcome import Outcome
from backend.schemas.scenario import ScenarioSpec


class TestLanggraphAgentToolUsage:
    """Test suite for Langgraph agent tool usage patterns."""

    @pytest.fixture
    def mock_scenario_spec(self):
        """Create a mock scenario specification for testing."""
        return ScenarioSpec(
            id="test_scenario",
            name="Test Scenario",  # Fixed: was title, now name
            seed=12345,  # Added required field
            state={"location": "test_room", "time": 0},
            entities=[{"id": "player", "type": "player", "name": "Test Player"}],
            actions=[],
            random_events=[],  # Added required field
            loss_conditions=[  # Added required field
                {
                    "id": "test_loss",
                    "condition": {"==": [{"var": "health"}, 0]},
                    "message": "Test loss condition",
                },
                {
                    "id": "test_loss2",
                    "condition": {">=": [{"var": "time"}, 1000]},
                    "message": "Time limit exceeded",
                },
            ],
            negativity_budget={  # Added required field
                "min_fail_rate": 0.1,
                "decay_per_turn": {"default": 0.05},
            },
            rules=[],
        )

    @pytest.fixture
    def orchestrator(self, mock_scenario_spec):
        """Create a TurnOrchestrator instance for testing."""
        with patch("backend.engine.orchestrator.create_provider") as mock_provider:
            mock_provider.return_value = AsyncMock()
            orchestrator = TurnOrchestrator(
                spec=mock_scenario_spec, session_id="test_session", db_manager=None
            )
            return orchestrator

    def test_agent_state_schema_completeness(self):
        """Test that AgentState schema includes all required fields."""
        # Test we can create a complete agent state
        state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "game_state": {"test": True},
            "entities": [{"id": "test"}],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {"test": True},
            "user_input": "test input",
            "conversation_summary": {"total_messages": 1},
            "memory_state": {"turn_count": 1},
            "error_recovery_active": False,
            "error_context": None,
        }

        # Verify all fields are accessible
        assert state["messages"] is not None
        assert state["game_state"]["test"] is True
        assert state["session_id"] == "test"
        assert state["error_recovery_active"] is False

    def test_build_context_from_state(self, orchestrator):
        """Test building context from agent state."""
        state: AgentState = {
            "messages": [],
            "game_state": {"location": "test_room", "score": 100},
            "entities": [{"id": "player", "type": "player"}],
            "session_id": "test",
            "turn_count": 5,
            "tool_results": [],
            "context": None,
            "user_input": "explore",
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        context = orchestrator._build_context_from_state(state)

        assert context["state"] == state["game_state"]
        assert context["entities"] == state["entities"]
        assert context["turn"] == 5
        assert "available_actions" in context

    def test_should_continue_routing_logic(self, orchestrator):
        """Test the enhanced conditional routing logic."""
        # Test routing to tools when tool calls present
        ai_message_with_tools = AIMessage(
            content="I need to check something",
            tool_calls=[{"name": "read_state", "args": {}, "id": "test_id"}],
        )
        state_with_tools: AgentState = {
            "messages": [ai_message_with_tools],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        assert orchestrator._should_continue(state_with_tools) == "tools"

        # Test routing to outcome when max rounds reached
        state_max_rounds: AgentState = {
            "messages": [AIMessage(content="Thinking...")],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [{"test": i} for i in range(6)],  # Exceeds max_rounds=5
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        assert orchestrator._should_continue(state_max_rounds) == "outcome"

        # Test routing based on content keywords
        ai_message_narrative = AIMessage(
            content="Let me create the final narrative for this story."
        )
        state_narrative: AgentState = {
            "messages": [ai_message_narrative],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        assert orchestrator._should_continue(state_narrative) == "outcome"

    def test_check_for_errors_detection(self, orchestrator):
        """Test error detection in tool messages."""
        # Test with error messages
        error_tool_message = ToolMessage(
            content="Error: Tool execution failed", tool_call_id="test_id"
        )
        state_with_errors: AgentState = {
            "messages": [error_tool_message],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        assert orchestrator._check_for_errors(state_with_errors) == "error"

        # Test without errors
        success_tool_message = ToolMessage(
            content="Successfully updated state", tool_call_id="test_id"
        )
        state_no_errors: AgentState = {
            "messages": [success_tool_message],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        assert orchestrator._check_for_errors(state_no_errors) == "process"

    def test_analyze_tool_usage_patterns(self, orchestrator):
        """Test tool usage pattern analysis."""
        tool_messages = [
            ToolMessage(content="Successfully read state", tool_call_id="1"),
            ToolMessage(content="Error: Invalid parameters", tool_call_id="2"),
            ToolMessage(content="Updated game state successfully", tool_call_id="3"),
        ]

        state: AgentState = {
            "messages": tool_messages,
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        analysis = orchestrator._analyze_tool_usage(tool_messages, state)

        assert analysis["tool_count"] == 3
        assert analysis["success_rate"] == 2 / 3  # 2 successes out of 3
        assert analysis["state_modifications"] == 2  # Updated and read state operations
        assert analysis["effectiveness"] in ["medium", "high", "low"]

    def test_analyze_errors_categorization(self, orchestrator):
        """Test error analysis and categorization."""
        error_messages = [
            ToolMessage(content="Error: Resource not found", tool_call_id="1"),
            ToolMessage(content="Critical error: System failure", tool_call_id="2"),
            ToolMessage(content="Warning: Deprecated parameter", tool_call_id="3"),
        ]

        analysis = orchestrator._analyze_errors(error_messages)

        assert analysis["error_count"] == 3
        assert "missing_resource" in analysis["error_types"]
        assert analysis["severity"] == "high"  # Due to critical error
        assert analysis["recoverable"] is False

    def test_create_recovery_message_generation(self, orchestrator):
        """Test recovery message generation for different error types."""
        # Test critical error scenario
        critical_analysis = {
            "error_count": 2,
            "error_types": ["system"],
            "severity": "high",
            "recoverable": False,
        }

        message = orchestrator._create_recovery_message(critical_analysis)
        assert "critical" in message.content.lower()
        assert "narrative outcome" in message.content.lower()

        # Test recoverable error scenario
        recoverable_analysis = {
            "error_count": 1,
            "error_types": ["syntax"],
            "severity": "medium",
            "recoverable": True,
        }

        message = orchestrator._create_recovery_message(recoverable_analysis)
        assert "syntax" in message.content.lower()
        assert "parameters" in message.content.lower()

    def test_conversation_summarization(self, orchestrator):
        """Test conversation summarization functionality."""
        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User input"),
            AIMessage(
                content="AI response",
                tool_calls=[{"name": "read_state", "args": {}, "id": "tool_call_1"}],
            ),
            ToolMessage(content="Tool result", tool_call_id="1"),
            AIMessage(content="Final response"),
        ]

        summary = orchestrator._summarize_conversation(messages)

        assert summary["total_messages"] == 5
        assert summary["human_messages"] == 1
        assert summary["ai_messages"] == 2
        assert summary["tool_messages"] == 1
        assert "read_state" in summary["tools_used"]
        assert summary["last_user_input"] == "User input"

    def test_memory_state_snapshot(self, orchestrator):
        """Test memory state snapshot creation."""
        snapshot = orchestrator._get_memory_state_snapshot()

        assert "turn_count" in snapshot
        assert "session_id" in snapshot
        assert snapshot["session_id"] == "test_session"

    @pytest.mark.asyncio
    async def test_process_tool_results_integration(self, orchestrator):
        """Test tool result processing integration."""
        state: AgentState = {
            "messages": [
                ToolMessage(content="Successfully updated state", tool_call_id="1"),
                ToolMessage(content="Created new entity", tool_call_id="2"),
            ],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        result = await orchestrator._process_tool_results(state)

        assert "tool_results" in result
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["execution_count"] == 1
        assert result["tool_results"][0]["tools_in_batch"] == 2

    @pytest.mark.asyncio
    async def test_handle_errors_integration(self, orchestrator):
        """Test error handling integration."""
        state: AgentState = {
            "messages": [
                ToolMessage(content="Error: Tool failed", tool_call_id="1"),
                ToolMessage(content="Critical error occurred", tool_call_id="2"),
            ],
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        result = await orchestrator._handle_errors(state)

        assert "messages" in result
        assert "tool_results" in result
        assert "error_recovery_active" in result
        assert result["error_recovery_active"] is True
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], HumanMessage)


class TestAgentToolOrchestrationPerformance:
    """Performance tests for agent tool orchestration."""

    @pytest.fixture
    def performance_orchestrator(self):
        """Create orchestrator for performance testing."""
        spec = ScenarioSpec(
            id="perf_test",
            name="Performance Test",  # Fixed: was title, now name
            seed=12345,  # Added required field
            state={"test": True},
            entities=[],
            actions=[],
            random_events=[],  # Added required field
            loss_conditions=[  # Added required field
                {
                    "id": "perf_loss1",
                    "condition": {"==": [{"var": "test"}, False]},
                    "message": "Test failed",
                },
                {
                    "id": "perf_loss2",
                    "condition": {">=": [{"var": "time"}, 100]},
                    "message": "Time exceeded",
                },
            ],
            negativity_budget={  # Added required field
                "min_fail_rate": 0.1,
                "decay_per_turn": {"default": 0.05},
            },
            rules=[],
        )

        with patch("backend.engine.orchestrator.create_provider"):
            return TurnOrchestrator(spec, "perf_test_session")

    def test_routing_decision_performance(self, performance_orchestrator):
        """Test that routing decisions are made efficiently."""
        import time

        # Create a state with complex data
        complex_state: AgentState = {
            "messages": [
                AIMessage(
                    content="I need to analyze this complex situation and determine the best course of action for the narrative."
                )
            ]
            * 10,
            "game_state": {"location": f"room_{i}" for i in range(100)},
            "entities": [{"id": f"entity_{i}", "type": "npc"} for i in range(50)],
            "session_id": "perf_test",
            "turn_count": 1,
            "tool_results": [],
            "context": {"complex_data": list(range(1000))},
            "user_input": "complex action",
            "conversation_summary": {"tools_used": [f"tool_{i}" for i in range(20)]},
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        # Measure routing decision time
        start_time = time.time()
        result = performance_orchestrator._should_continue(complex_state)
        decision_time = time.time() - start_time

        # Should complete routing decision quickly (under 100ms)
        assert decision_time < 0.1
        assert result in ["tools", "outcome", "END"]

    def test_tool_analysis_performance(self, performance_orchestrator):
        """Test tool analysis performance with many tool messages."""
        import time

        # Create many tool messages
        tool_messages = [
            ToolMessage(
                content=f"Tool {i} executed successfully with result data",
                tool_call_id=f"id_{i}",
            )
            for i in range(100)
        ]

        state: AgentState = {
            "messages": tool_messages,
            "game_state": {},
            "entities": [],
            "session_id": "perf_test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
        }

        # Measure analysis time
        start_time = time.time()
        analysis = performance_orchestrator._analyze_tool_usage(
            tool_messages[:10], state
        )  # Analyze recent tools
        analysis_time = time.time() - start_time

        # Should complete analysis quickly
        assert analysis_time < 0.05
        assert analysis["tool_count"] == 10
        assert "effectiveness" in analysis

    def test_memory_snapshot_performance(self, performance_orchestrator):
        """Test memory state snapshot performance."""
        import time

        # Measure snapshot creation time
        start_time = time.time()
        snapshot = performance_orchestrator._get_memory_state_snapshot()
        snapshot_time = time.time() - start_time

        # Should be very fast
        assert snapshot_time < 0.01
        assert isinstance(snapshot, dict)
        assert "turn_count" in snapshot
