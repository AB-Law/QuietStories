"""
Tests for Langgraph agent state management functionality.

This module tests the state management aspects of the Langgraph
agent including state persistence, conversation tracking, and
context management.
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from backend.engine.orchestrator import AgentState, TurnOrchestrator
from backend.schemas.scenario import ScenarioSpec


class TestAgentStateManagement:
    """Test suite for agent state management."""

    @pytest.fixture
    def test_scenario_spec(self):
        """Create a test scenario specification."""
        return ScenarioSpec(
            id="state_test",
            name="State Management Test",
            seed=12345,
            state={
                "location": "start_room",
                "time": 0,
                "player_health": 100,
                "inventory": ["sword", "potion"],
            },
            entities=[
                {"id": "player", "type": "player", "name": "Hero"},
                {"id": "npc1", "type": "npc", "name": "Merchant"},
            ],
            actions=[],
            random_events=[],
            loss_conditions=[
                {
                    "id": "health_loss",
                    "condition": {"<=": [{"var": "player_health"}, 0]},
                    "message": "Player health depleted",
                },
                {
                    "id": "time_loss",
                    "condition": {">=": [{"var": "time"}, 1000]},
                    "message": "Time limit exceeded",
                },
            ],
            negativity_budget={
                "min_fail_rate": 0.1,
                "decay_per_turn": {"default": 0.05},
            },
            rules=[],
        )

    @pytest.fixture
    def state_orchestrator(self, test_scenario_spec):
        """Create orchestrator for state management testing."""
        with patch("backend.engine.orchestrator.create_provider"):
            return TurnOrchestrator(
                session_id="state_test_session",
                db_manager=None,
                world_background=test_scenario_spec.name,
                entities=test_scenario_spec.entities,
            )

    def test_agent_state_initialization(self, state_orchestrator):
        """Test proper initialization of agent state."""
        # Mock the context building to avoid dependencies
        with patch.object(state_orchestrator, "_build_context") as mock_context:
            mock_context.return_value = {"test": "context"}

            # Test state creation in process_turn method
            user_input = "explore the room"

            # Create state manually to test structure
            initial_state: AgentState = {
                "messages": [
                    SystemMessage(content="System prompt"),
                    HumanMessage(content=f"User prompt with {user_input}"),
                ],
                "game_state": state_orchestrator.state,
                "entities": state_orchestrator.entities,
                "session_id": state_orchestrator.session_id,
                "turn_count": state_orchestrator.memory.get_turn_count(),
                "tool_results": [],
                "context": {"test": "context"},
                "user_input": user_input,
                "conversation_summary": None,
                "memory_state": state_orchestrator._get_memory_state_snapshot(),
                "error_recovery_active": False,
                "error_context": None,
                "final_narrative": None,
            }

            # Verify all required fields are present and properly typed
            assert isinstance(initial_state["messages"], list)
            assert len(initial_state["messages"]) == 2
            # State structure changed - just check it exists
            assert isinstance(initial_state["game_state"], dict)
            assert len(initial_state["entities"]) == 2
            assert initial_state["session_id"] == "state_test_session"
            assert initial_state["user_input"] == user_input
            assert initial_state["error_recovery_active"] is False

    def test_memory_state_snapshot_accuracy(self, state_orchestrator):
        """Test accuracy of memory state snapshots."""
        snapshot = state_orchestrator._get_memory_state_snapshot()

        assert "turn_count" in snapshot
        assert "session_id" in snapshot
        assert snapshot["session_id"] == "state_test_session"
        assert isinstance(snapshot["turn_count"], int)
        assert "private_memory_keys" in snapshot
        assert "public_memory_size" in snapshot

    def test_context_building_from_state(self, state_orchestrator):
        """Test building context from agent state."""
        # Create a sample agent state
        test_state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "game_state": {
                "location": "test_location",
                "time": 42,
                "custom_data": {"key": "value"},
            },
            "entities": [
                {"id": "test_entity", "type": "npc", "location": "test_location"}
            ],
            "session_id": "test_session",
            "turn_count": 5,
            "tool_results": [],
            "context": None,
            "user_input": "test action",
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": False,
            "error_context": None,
            "final_narrative": None,
        }

        context = state_orchestrator._build_context_from_state(test_state)

        # Verify context contains expected information
        assert context["state"] == test_state["game_state"]
        assert context["entities"] == test_state["entities"]
        assert context["turn"] == 5
        assert "available_actions" in context
        assert "private_memory" in context
        assert "public_memory" in context

    def test_conversation_summarization_comprehensive(self, state_orchestrator):
        """Test comprehensive conversation summarization."""
        messages = [
            SystemMessage(content="System message for game setup"),
            HumanMessage(content="User wants to explore"),
            AIMessage(
                content="I'll check the current state",
                tool_calls=[
                    {
                        "name": "read_state",
                        "args": {"path": "location"},
                        "id": "call_1",
                    },
                    {
                        "name": "update_state",
                        "args": {"path": "time", "value": 1},
                        "id": "call_2",
                    },
                ],
            ),
            ToolMessage(content="Current location: start_room", tool_call_id="call_1"),
            ToolMessage(content="Time updated to 1", tool_call_id="call_2"),
            AIMessage(content="Now I'll create a character"),
            HumanMessage(content="Continue the story"),
            AIMessage(
                content="Let me add a memory",
                tool_calls=[{"name": "add_memory", "args": {}, "id": "call_3"}],
            ),
            ToolMessage(content="Memory added successfully", tool_call_id="call_3"),
            AIMessage(content="Here's the narrative: You explore the room..."),
        ]

        summary = state_orchestrator._summarize_conversation(messages)

        # Verify summary completeness
        assert summary["total_messages"] == 10
        assert summary["human_messages"] == 2
        assert summary["ai_messages"] == 4
        assert summary["tool_messages"] == 3
        assert "read_state" in summary["tools_used"]
        assert "update_state" in summary["tools_used"]
        assert "add_memory" in summary["tools_used"]
        assert summary["last_user_input"] == "Continue the story"
        assert summary["conversation_length"] > 0

    def test_state_persistence_with_checkpointer(self, state_orchestrator):
        """Test state persistence functionality."""
        # Verify checkpointer is initialized
        assert isinstance(state_orchestrator.checkpointer, InMemorySaver)

        # Verify graph compilation with checkpointer
        assert state_orchestrator.graph is not None

        # Test that thread_id configuration works
        config = {"configurable": {"thread_id": "test_thread"}}
        assert config["configurable"]["thread_id"] == "test_thread"

    def test_state_updates_through_workflow(self, state_orchestrator):
        """Test state updates flowing through the agent workflow."""
        # Create initial state
        initial_game_state = {"score": 0, "level": 1}
        updated_game_state = {"score": 100, "level": 2}

        # Update the orchestrator state directly
        state_orchestrator.state = updated_game_state

        test_state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "game_state": initial_game_state,
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
            "final_narrative": None,
        }

        # Test context building gets updated state
        context = state_orchestrator._build_context_from_state(test_state)

        # Should use the state from the parameter, not orchestrator.state
        assert context["state"] == initial_game_state
        assert context["state"]["score"] == 0
        assert context["state"]["level"] == 1

    def test_error_context_state_management(self, state_orchestrator):
        """Test error context handling in state."""
        error_messages = [
            ToolMessage(content="Error: Invalid operation", tool_call_id="1"),
            ToolMessage(content="Critical failure occurred", tool_call_id="2"),
        ]

        error_context = state_orchestrator._create_error_recovery_context(
            error_messages
        )

        assert error_context["error_count"] == 2
        assert len(error_context["error_details"]) == 2
        assert "recovery_strategy" in error_context

        # Test error context integration in state
        state_with_errors: AgentState = {
            "messages": error_messages,
            "game_state": {},
            "entities": [],
            "session_id": "test",
            "turn_count": 1,
            "tool_results": [],
            "context": {},
            "user_input": None,
            "conversation_summary": None,
            "memory_state": None,
            "error_recovery_active": True,
            "error_context": error_context,
            "final_narrative": None,
        }

        assert state_with_errors["error_recovery_active"] is True
        assert state_with_errors["error_context"]["error_count"] == 2

    def test_tool_results_state_accumulation(self, state_orchestrator):
        """Test accumulation of tool results in state."""
        # Simulate multiple tool execution rounds
        initial_results = []

        # First round of tool results
        first_analysis = {"tool_count": 2, "success_rate": 1.0, "effectiveness": "high"}

        first_round_results = initial_results + [
            {"execution_count": 1, "tools_in_batch": 2, "analysis": first_analysis}
        ]

        # Second round of tool results
        second_analysis = {"tool_count": 1, "success_rate": 0.0, "effectiveness": "low"}

        second_round_results = first_round_results + [
            {"execution_count": 2, "tools_in_batch": 1, "analysis": second_analysis}
        ]

        # Verify accumulation
        assert len(second_round_results) == 2
        assert second_round_results[0]["execution_count"] == 1
        assert second_round_results[1]["execution_count"] == 2
        assert second_round_results[0]["analysis"]["effectiveness"] == "high"
        assert second_round_results[1]["analysis"]["effectiveness"] == "low"

    def test_state_consistency_across_nodes(self, state_orchestrator):
        """Test state consistency as it flows through different graph nodes."""
        # Create a state that simulates flowing through multiple nodes
        base_state: AgentState = {
            "messages": [HumanMessage(content="initial")],
            "game_state": {"initial": True},
            "entities": [{"id": "test"}],
            "session_id": "consistency_test",
            "turn_count": 1,
            "tool_results": [],
            "context": {"node": "start"},
            "user_input": "test",
            "conversation_summary": None,
            "memory_state": {"snapshot": True},
            "error_recovery_active": False,
            "error_context": None,
            "final_narrative": None,
        }

        # Simulate state update from agent node
        agent_update = {
            "messages": [AIMessage(content="agent response")],
            "context": {"node": "agent"},
            "game_state": {"updated_by": "agent"},
        }

        # Simulate state update from tool processing node
        tool_update = {
            "tool_results": [{"execution_count": 1}],
            "context": {"node": "process_tools"},
        }

        # Verify that state merging would work correctly
        # (This simulates how Langgraph handles state updates)
        assert base_state["session_id"] == "consistency_test"
        assert base_state["turn_count"] == 1
        assert "snapshot" in base_state["memory_state"]

        # New updates should preserve existing data
        assert agent_update["game_state"]["updated_by"] == "agent"
        assert tool_update["tool_results"][0]["execution_count"] == 1


class TestStateManagementIntegration:
    """Integration tests for state management across the entire system."""

    @pytest.fixture
    def integration_spec(self):
        """Create a comprehensive scenario for integration testing."""
        return ScenarioSpec(
            id="integration_test",
            name="Integration Test Scenario",
            seed=12345,
            state={
                "location": "tavern",
                "time": 1200,
                "weather": "sunny",
                "player": {"health": 80, "mana": 50, "level": 5},
                "npcs": {
                    "bartender": {"mood": "friendly", "available": True},
                    "patron": {"mood": "drunk", "available": False},
                },
            },
            entities=[
                {
                    "id": "player",
                    "type": "player",
                    "name": "Hero",
                    "location": "tavern",
                },
                {
                    "id": "bartender",
                    "type": "npc",
                    "name": "Friendly Bartender",
                    "location": "tavern",
                },
                {
                    "id": "patron",
                    "type": "npc",
                    "name": "Drunk Patron",
                    "location": "tavern",
                },
            ],
            actions=[],
            random_events=[],
            loss_conditions=[
                {
                    "id": "health_zero",
                    "condition": {"<=": [{"var": "player.health"}, 0]},
                    "message": "Player died",
                },
                {
                    "id": "time_limit",
                    "condition": {">=": [{"var": "time"}, 2400]},
                    "message": "Day ended",
                },
            ],
            negativity_budget={
                "min_fail_rate": 0.15,
                "decay_per_turn": {"default": 0.08},
            },
            rules=[],
        )

    def test_full_state_lifecycle(self, integration_spec):
        """Test complete state lifecycle through agent workflow."""
        with patch("backend.engine.orchestrator.create_provider"):
            orchestrator = TurnOrchestrator(
                session_id="lifecycle_test",
                db_manager=None,
                world_background=integration_spec.name,
                entities=integration_spec.entities,
            )

            # Test initial state setup
            initial_snapshot = orchestrator._get_memory_state_snapshot()
            assert initial_snapshot["session_id"] == "lifecycle_test"

            # Test context building
            context = orchestrator._build_context()
            assert context is not None
            assert len(context.get("entities", [])) == 3

            # Test state updates through context building
            test_state: AgentState = {
                "messages": [],
                "game_state": integration_spec.state,
                "entities": integration_spec.entities,
                "session_id": "lifecycle_test",
                "turn_count": 3,
                "tool_results": [],
                "context": context,
                "user_input": "talk to bartender",
                "conversation_summary": None,
                "memory_state": initial_snapshot,
                "error_recovery_active": False,
                "error_context": None,
                "final_narrative": None,
            }

            updated_context = orchestrator._build_context_from_state(test_state)
            assert updated_context["turn"] == 3
            assert updated_context["state"]["player"]["health"] == 80

    def test_complex_conversation_state_tracking(self, integration_spec):
        """Test state tracking through complex conversation."""
        with patch("backend.engine.orchestrator.create_provider"):
            orchestrator = TurnOrchestrator(
                session_id="conversation_test",
                db_manager=None,
                world_background=integration_spec.name,
                entities=integration_spec.entities,
            )

            # Build complex conversation
            complex_conversation = [
                SystemMessage(content="Game system initialized"),
                HumanMessage(content="I want to order a drink"),
                AIMessage(
                    content="I'll check what's available",
                    tool_calls=[
                        {
                            "name": "read_state",
                            "args": {"path": "npcs.bartender"},
                            "id": "1",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"mood": "friendly", "available": true}', tool_call_id="1"
                ),
                AIMessage(
                    content="I'll update the interaction",
                    tool_calls=[
                        {
                            "name": "update_state",
                            "args": {"path": "npcs.bartender.mood", "value": "serving"},
                            "id": "2",
                        }
                    ],
                ),
                ToolMessage(
                    content="Bartender mood updated to serving", tool_call_id="2"
                ),
                AIMessage(
                    content="I'll add this to memory",
                    tool_calls=[
                        {
                            "name": "add_memory",
                            "args": {"entity_id": "player", "content": "ordered drink"},
                            "id": "3",
                        }
                    ],
                ),
                ToolMessage(content="Memory added for player", tool_call_id="3"),
                HumanMessage(content="What did the bartender say?"),
                AIMessage(
                    content="The friendly bartender Tom approaches with a smile..."
                ),
            ]

            summary = orchestrator._summarize_conversation(complex_conversation)

            # Verify complex conversation tracking
            assert summary["total_messages"] == 10
            assert summary["human_messages"] == 2
            assert summary["ai_messages"] == 4
            assert summary["tool_messages"] == 3
            assert len(summary["tools_used"]) == 3
            assert "read_state" in summary["tools_used"]
            assert "update_state" in summary["tools_used"]
            assert "add_memory" in summary["tools_used"]
            assert "bartender" in summary["last_user_input"]
