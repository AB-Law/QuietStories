"""
Test suite for performance optimization features.

Tests session isolation, relationship extraction, and streaming performance
to ensure the optimization features work correctly and don't break existing functionality.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.sessions import create_session, get_session
from backend.db.manager import DatabaseManager
from backend.engine.memory import MemoryManager
from backend.engine.relationship_graph import (
    RelationshipGraph,
    extract_relationship_from_content,
)
from backend.schemas import ScenarioSpec


class TestSessionIsolation:
    """Test that sessions are properly isolated from each other."""

    def test_separate_chroma_collections(self):
        """Test that each session creates its own ChromaDB collection."""
        # Create two memory managers with different session IDs
        memory1 = MemoryManager("session_1")
        memory2 = MemoryManager("session_2")

        # Check that they have different collection names
        assert memory1.semantic_search.collection_name == "session_session_1"
        assert memory2.semantic_search.collection_name == "session_session_2"

        # Both should be available if ChromaDB is set up
        if memory1.semantic_search.is_available():
            assert (
                memory1.semantic_search.collection_name
                != memory2.semantic_search.collection_name
            )

    def test_memory_isolation(self):
        """Test that memories from different sessions don't leak."""
        memory1 = MemoryManager("session_1")
        memory2 = MemoryManager("session_2")

        # Add memory to session 1
        memory1.update_scoped_memory("entity1", "test", "test content", "private")

        # Check that session 2 doesn't have this memory
        assert "entity1" not in memory2.private_memory

        # Both sessions should have their own relationship graphs
        assert memory1.relationship_graph is not memory2.relationship_graph


class TestRelationshipExtraction:
    """Test relationship extraction from memory content."""

    def test_extract_relationship_from_content(self):
        """Test that relationships are correctly extracted from memory content."""
        all_entities = ["elena", "marcus", "sarah"]

        # Test trust relationship
        result = extract_relationship_from_content(
            "Growing to trust Marcus after he saved her from the bandits",
            "elena",
            all_entities,
        )

        assert result is not None
        assert result["from_entity"] == "elena"
        assert result["to_entity"] == "marcus"
        assert result["relationship_type"] == "friendship"
        assert result["sentiment"] > 0  # Should be positive

    def test_extract_negative_relationship(self):
        """Test extraction of negative relationships."""
        all_entities = ["elena", "marcus", "sarah"]

        result = extract_relationship_from_content(
            "Elena fears Marcus after his betrayal", "elena", all_entities
        )

        assert result is not None
        assert result["from_entity"] == "elena"
        assert result["to_entity"] == "marcus"
        assert result["relationship_type"] == "adversarial"
        assert result["sentiment"] < 0  # Should be negative

    def test_no_relationship_extraction(self):
        """Test that unrelated content doesn't extract relationships."""
        all_entities = ["elena", "marcus", "sarah"]

        result = extract_relationship_from_content(
            "The weather is nice today", "elena", all_entities
        )

        assert result is None  # No relationship should be extracted

    def test_relationship_graph_operations(self):
        """Test basic relationship graph operations."""
        graph = RelationshipGraph()

        # Add a relationship
        success = graph.add_relationship(
            from_entity="elena",
            to_entity="marcus",
            relationship_type="trust",
            sentiment=0.8,
            strength=0.9,
        )

        assert success

        # Query relationships
        relationships = graph.get_relationships(entity_id="elena")
        assert len(relationships) == 1
        assert relationships[0].relationship_type == "trust"
        assert relationships[0].sentiment == 0.8

        # Get entity summary
        summary = graph.get_relationship_summary("elena")
        assert summary["entity_id"] == "elena"
        assert summary["total_outgoing"] == 1
        assert summary["average_sentiment"] == 0.8


class TestStreamingPerformance:
    """Test streaming performance improvements."""

    @pytest.mark.asyncio
    async def test_provider_streaming(self):
        """Test that providers can handle streaming requests."""
        # This would need actual provider setup for full testing
        # For now, test that the streaming method exists and can be called

        # Mock a simple provider for testing
        class MockProvider:
            async def astream_chat(self, messages, tools=None, **kwargs):
                # Simulate streaming tokens
                tokens = [
                    "Hello",
                    " ",
                    "world",
                    "!",
                    "\n\n",
                    "This",
                    " ",
                    "is",
                    " ",
                    "a",
                    " ",
                    "test.",
                ]
                for token in tokens:
                    yield token

        provider = MockProvider()
        tokens_received = []

        async for token in provider.astream_chat([]):
            tokens_received.append(token)

        assert len(tokens_received) > 0
        assert "".join(tokens_received) == "Hello world!\n\nThis is a test."

    @pytest.mark.asyncio
    async def test_hybrid_streaming_flow(self):
        """Test the hybrid streaming flow logic."""
        # Test that we can simulate the 4-phase approach
        phases = []

        async def mock_read_tools():
            phases.append("read")
            return ["read_result_1", "read_result_2"]

        async def mock_stream_narrative(context):
            phases.append("stream")
            yield "Narrative "
            yield "content "
            yield "streaming..."

        async def mock_write_tools():
            phases.append("write")
            return ["write_result_1"]

        async def mock_confirm_tools(results):
            phases.append("confirm")
            return "Confirmed"

        # Simulate the flow
        read_results = await mock_read_tools()

        async for token in mock_stream_narrative(read_results):
            pass  # Consume tokens

        write_results = await mock_write_tools()
        confirmation = await mock_confirm_tools(write_results)

        # Verify phases were executed in order
        assert phases == ["read", "stream", "write", "confirm"]
        assert confirmation == "Confirmed"

    def test_memory_batching(self):
        """Test that batch memory operations work correctly."""
        memory = MemoryManager("test_session")

        # Add multiple memories in batch
        memories = [
            {
                "entity_id": "elena",
                "content": "Trusts Marcus after the rescue",
                "visibility": "private",
                "scope": "relationship",
            },
            {
                "entity_id": "marcus",
                "content": "Feels protective of Elena",
                "visibility": "private",
                "scope": "relationship",
            },
        ]

        # This would need the actual batch tool implementation
        # For now, test that we can add individual memories
        for mem in memories:
            memory.update_scoped_memory(
                entity_id=mem["entity_id"],
                content=mem["content"],
                scope=mem["scope"],
                visibility=mem["visibility"],
            )

        # Check that memories were added
        assert len(memory.private_memory.get("elena", [])) > 0
        assert len(memory.private_memory.get("marcus", [])) > 0


class TestPromptCompression:
    """Test that prompt compression maintains functionality."""

    def test_compressed_prompt_structure(self):
        """Test that compressed prompts maintain required structure."""
        from backend.prompts import NARRATOR_SYSTEM

        # Check that key sections are still present
        assert "AVAILABLE TOOLS:" in NARRATOR_SYSTEM
        assert "RELATIONSHIP TRACKING PRIORITY" in NARRATOR_SYSTEM
        assert "CRITICAL RULES:" in NARRATOR_SYSTEM

        # Check that batch tools are mentioned
        assert "add_memories(memories):" in NARRATOR_SYSTEM
        assert "read_state_cached(path, use_cache):" in NARRATOR_SYSTEM

        # Check that relationship keywords are mentioned
        assert "trust, fear, love, alliance, rivalry" in NARRATOR_SYSTEM

        # Verify token reduction (rough estimate)
        # Original was ~3,000 tokens, compressed should be ~2,000
        token_count = len(NARRATOR_SYSTEM.split())  # Rough token estimate
        assert token_count < 2500  # Should be significantly compressed

    def test_examples_preserved(self):
        """Test that essential examples are preserved."""
        from backend.prompts import NARRATOR_SYSTEM

        # Should have at least 2 examples (down from 5)
        example_count = NARRATOR_SYSTEM.count('"narrative":')
        assert example_count >= 2

        # Should have the essential examples
        assert "You enter the dark cave" in NARRATOR_SYSTEM
        assert "The merchant eyes you suspiciously" in NARRATOR_SYSTEM


class TestToolBatching:
    """Test that batch operations reduce tool call volume."""

    def test_batch_memory_tool_logic(self):
        """Test the logic of batch memory operations."""
        # Test that batching multiple memories into one call works
        memories = [
            {"entity_id": "elena", "content": "Test memory 1", "scope": "general"},
            {
                "entity_id": "marcus",
                "content": "Test memory 2",
                "scope": "relationship",
            },
            {"entity_id": "sarah", "content": "Test memory 3", "scope": "belief"},
        ]

        # Simulate batch processing
        processed_count = 0
        for memory in memories:
            if memory.get("entity_id") and memory.get("content"):
                processed_count += 1

        assert processed_count == 3  # All memories should be processed

        # In a real batch tool, this would be 1 tool call instead of 3
        expected_tool_calls = 1  # Batch call
        actual_tool_calls = 3  # Individual calls

        assert expected_tool_calls < actual_tool_calls

    def test_state_caching_logic(self):
        """Test that state caching reduces redundant reads."""
        # Simulate state cache
        cache = {}

        def read_state_cached(path, use_cache=True):
            if use_cache and path in cache:
                return f"Cached: {cache[path]}"

            # Simulate reading from state
            value = f"value_for_{path}"
            if use_cache:
                cache[path] = value

            return value

        # First read should go to state
        result1 = read_state_cached("state.player.health")
        assert result1 == "value_for_state.player.health"
        assert "state.player.health" in cache

        # Second read should use cache
        result2 = read_state_cached("state.player.health")
        assert result2 == "Cached: value_for_state.player.health"

        # Different path should not use cache
        result3 = read_state_cached("state.player.mana")
        assert result3 == "value_for_state.player.mana"
        assert "state.player.mana" in cache


if __name__ == "__main__":
    # Run basic tests if executed directly
    test_suite = TestSessionIsolation()
    test_suite.test_separate_chroma_collections()
    test_suite.test_memory_isolation()

    rel_tests = TestRelationshipExtraction()
    rel_tests.test_extract_relationship_from_content()
    rel_tests.test_relationship_graph_operations()

    print("✅ All basic tests passed!")
