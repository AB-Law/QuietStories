"""
Tests for performance tracking and metrics collection.

This module tests the new performance tracking features:
- Timing decorators
- Performance metrics collection
- API endpoints for metrics
"""

import asyncio
import time

import pytest

from backend.utils.debug import PerformanceMetrics, get_performance_metrics, time_it


class TestPerformanceMetrics:
    """Test performance metrics collection."""

    def test_metrics_initialization(self):
        """Test metrics tracker initialization."""
        metrics = PerformanceMetrics()

        assert "llm_calls" in metrics.metrics
        assert "tool_executions" in metrics.metrics
        assert "turn_processing" in metrics.metrics
        assert len(metrics.start_times) == 0

    def test_operation_timing(self):
        """Test operation timing tracking."""
        metrics = PerformanceMetrics()

        # Start an operation
        metrics.start_operation("test_op_1", "llm_call")
        assert "test_op_1" in metrics.start_times

        # Simulate some work
        time.sleep(0.1)

        # End the operation
        metrics.end_operation("test_op_1", "llm_call", metadata={"test": "data"})

        # Verify metrics were recorded
        assert len(metrics.metrics["llm_calls"]) == 1
        assert metrics.metrics["llm_calls"][0]["operation_id"] == "test_op_1"
        assert metrics.metrics["llm_calls"][0]["duration_ms"] >= 100  # At least 100ms
        assert metrics.metrics["llm_calls"][0]["metadata"]["test"] == "data"

    def test_multiple_operations(self):
        """Test tracking multiple operations."""
        metrics = PerformanceMetrics()

        # Start multiple operations
        for i in range(3):
            metrics.start_operation(f"op_{i}", "tool_execution")
            time.sleep(0.05)
            metrics.end_operation(f"op_{i}", "tool_execution")

        # Verify all operations were tracked
        assert len(metrics.metrics["tool_executions"]) == 3

    def test_get_summary(self):
        """Test summary statistics generation."""
        metrics = PerformanceMetrics()

        # Add some operations
        for i in range(5):
            metrics.start_operation(f"llm_{i}", "llm_call")
            time.sleep(0.01)
            metrics.end_operation(f"llm_{i}", "llm_call")

        summary = metrics.get_summary()

        # Verify summary structure
        assert "llm_calls" in summary
        assert summary["llm_calls"]["count"] == 5
        assert summary["llm_calls"]["total_time_ms"] > 0
        assert summary["llm_calls"]["avg_time_ms"] > 0
        assert summary["llm_calls"]["min_time_ms"] > 0
        assert summary["llm_calls"]["max_time_ms"] > 0
        assert len(summary["llm_calls"]["recent_operations"]) == 5

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        metrics = PerformanceMetrics()

        # Add some operations
        metrics.start_operation("test_op", "llm_call")
        metrics.end_operation("test_op", "llm_call")

        assert len(metrics.metrics["llm_calls"]) == 1

        # Reset metrics
        metrics.reset()

        assert len(metrics.metrics["llm_calls"]) == 0
        assert len(metrics.start_times) == 0

    def test_global_metrics_instance(self):
        """Test global metrics singleton."""
        metrics1 = get_performance_metrics()
        metrics2 = get_performance_metrics()

        # Should be the same instance
        assert metrics1 is metrics2


class TestTimingDecorator:
    """Test the @time_it decorator."""

    @pytest.mark.asyncio
    async def test_async_function_timing(self):
        """Test timing an async function."""

        @time_it
        async def async_test_func():
            await asyncio.sleep(0.1)
            return "done"

        result = await async_test_func()
        assert result == "done"

    def test_sync_function_timing(self):
        """Test timing a synchronous function."""

        @time_it
        def sync_test_func():
            time.sleep(0.05)
            return "completed"

        result = sync_test_func()
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_async_function_error_handling(self):
        """Test error handling in async functions."""

        @time_it
        async def failing_async_func():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_async_func()

    def test_sync_function_error_handling(self):
        """Test error handling in sync functions."""

        @time_it
        def failing_sync_func():
            time.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_sync_func()


class TestPerformanceOptimization:
    """Test performance optimization features."""

    def test_read_write_tool_categorization(self):
        """Test that tools are correctly categorized as read-only or write."""
        from backend.engine.orchestrator import READ_ONLY_TOOLS, WRITE_TOOLS

        # Verify no overlap between read and write tools
        overlap = READ_ONLY_TOOLS & WRITE_TOOLS
        assert len(overlap) == 0, f"Tools should not be in both categories: {overlap}"

        # Verify expected tools are in categories
        assert "read_state" in READ_ONLY_TOOLS
        assert "search_memories" in READ_ONLY_TOOLS
        assert "add_memory" in WRITE_TOOLS
        assert "update_state" in WRITE_TOOLS

    def test_performance_config_defaults(self):
        """Test default performance configuration values."""
        from backend.config import settings

        # Verify performance settings have sensible defaults
        assert hasattr(settings, "enable_performance_tracking")
        assert hasattr(settings, "max_parallel_tool_calls")
        assert settings.max_parallel_tool_calls > 0


@pytest.mark.asyncio
async def test_end_to_end_performance_tracking():
    """Test end-to-end performance tracking in a simulated workflow."""
    metrics = PerformanceMetrics()

    # Simulate a turn with multiple operations
    turn_id = "turn_test_1"
    metrics.start_operation(turn_id, "turn_processing")

    # Simulate LLM call
    llm_id = "llm_call_1"
    metrics.start_operation(llm_id, "llm_call")
    await asyncio.sleep(0.05)
    metrics.end_operation(llm_id, "llm_call", metadata={"tool_calls": 2, "tokens": 150})

    # Simulate tool executions
    for i in range(2):
        tool_id = f"tool_{i}"
        metrics.start_operation(tool_id, "tool_execution")
        await asyncio.sleep(0.02)
        metrics.end_operation(
            tool_id, "tool_execution", metadata={"tool_name": f"test_tool_{i}"}
        )

    # End turn
    await asyncio.sleep(0.01)
    metrics.end_operation(
        turn_id, "turn_processing", metadata={"user_input": True, "state_changes": 1}
    )

    # Verify metrics
    summary = metrics.get_summary()

    assert summary["turn_processing"]["count"] == 1
    assert summary["llm_calls"]["count"] == 1
    assert summary["tool_executions"]["count"] == 2

    # Verify timing relationships (turn should be longest)
    turn_time = summary["turn_processing"]["total_time_ms"]
    llm_time = summary["llm_calls"]["total_time_ms"]
    tool_time = summary["tool_executions"]["total_time_ms"]

    assert turn_time > llm_time
    assert turn_time > tool_time
