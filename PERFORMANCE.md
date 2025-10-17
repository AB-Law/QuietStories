# Performance Optimization Guide

This guide explains the performance improvements in QuietStories and how to monitor and optimize LLM call performance.

## Overview

QuietStories includes comprehensive performance tracking and optimization features to reduce LLM response latency and improve the overall user experience. The main improvements include:

1. **Detailed Performance Metrics**: Track LLM calls, tool executions, and turn processing times
2. **Parallel Tool Execution**: Tools are executed in parallel by default using LangGraph's ToolNode
3. **Tool Categorization**: Tools are categorized as read-only or write operations for better optimization
4. **Performance Monitoring API**: Endpoints to monitor and analyze performance in real-time

## Performance Tracking

### Automatic Timing

All critical operations are automatically timed:

- **LLM Calls**: Each call to the LLM provider is timed and logged
- **Tool Executions**: Individual tool calls and batch executions are tracked
- **Turn Processing**: Complete turn processing from start to finish

### Structured Logging

Performance logs include structured metadata for analysis:

```json
{
  "component": "Performance",
  "function": "process_turn",
  "duration_ms": 2450.5,
  "duration_s": 2.4505,
  "status": "success"
}
```

### Performance Metrics API

#### Get Current Metrics

```bash
GET /optimization/performance/metrics
```

Returns comprehensive performance statistics:

```json
{
  "status": "success",
  "metrics": {
    "llm_calls": {
      "count": 10,
      "total_time_ms": 15234.5,
      "avg_time_ms": 1523.45,
      "min_time_ms": 892.3,
      "max_time_ms": 2456.7,
      "recent_operations": [...]
    },
    "tool_executions": {
      "count": 25,
      "total_time_ms": 3421.2,
      "avg_time_ms": 136.85,
      ...
    },
    "turn_processing": {
      "count": 5,
      "total_time_ms": 18934.8,
      "avg_time_ms": 3786.96,
      ...
    }
  }
}
```

#### Reset Metrics

```bash
POST /optimization/performance/reset
```

Clears all collected performance metrics. Useful for:
- Starting fresh measurements
- Analyzing specific scenarios
- Reducing memory usage in long-running sessions

## Tool Optimization

### Parallel Execution

LangGraph's ToolNode automatically executes multiple tool calls in parallel, significantly reducing latency when the LLM requests multiple tools.

**Example**: If the LLM calls 3 tools that each take 200ms:
- **Sequential**: 600ms total
- **Parallel**: ~200ms total (3x faster!)

### Tool Categorization

Tools are categorized to help identify optimization opportunities:

#### Read-Only Tools (Safe for Parallel Execution)
- `read_state`: Read current game state
- `search_memories`: Search entity memories
- `query_relationships`: Query character relationships
- `semantic_search`: Semantic memory search
- `stateful_read`: Read state with conditions

#### Write Tools (May Have Side Effects)
- `add_memory`: Add new memory entry
- `update_state`: Modify game state
- `update_world`: Update world state
- `create_character`: Create new entity
- `batch_memory`: Batch memory operations

### Performance Metrics in Logs

Tool execution logs include detailed metrics:

```
[Tools] Executed 5 tools in 0.234s (avg: 46.8ms/tool)
{
  "tool_count": 5,
  "read_only_count": 3,
  "write_count": 2,
  "duration_ms": 234.0,
  "avg_time_per_tool_ms": 46.8
}
```

## Configuration

### Environment Variables

Add these to your `.env` file to control performance features:

```bash
# Enable/disable performance tracking
ENABLE_PERFORMANCE_TRACKING=true

# Maximum parallel tool calls (handled by LangGraph)
MAX_PARALLEL_TOOL_CALLS=10

# Verbose logging for debugging
VERBOSE_ORCHESTRATOR=true
LOG_MESSAGE_SEQUENCES=true
```

### Context Optimization

Configure context optimization to reduce token usage and improve speed:

```bash
POST /optimization/configure
{
  "max_turn_history": 10,
  "max_memories_per_entity": 10,
  "max_context_tokens": 4000,
  "enable_caching": true
}
```

## Monitoring Best Practices

### 1. Establish Baseline Performance

Before making changes:

```bash
# Reset metrics
POST /optimization/performance/reset

# Run your scenario
# ...

# Get baseline metrics
GET /optimization/performance/metrics
```

### 2. Identify Bottlenecks

Look for:
- High `max_time_ms` values (outliers)
- Large differences between `min_time_ms` and `max_time_ms`
- High `avg_time_ms` for specific operation types

### 3. Compare Before/After

Use the reset endpoint to measure improvements:

```bash
# Measure with old configuration
POST /optimization/performance/reset
# Run scenario...
GET /optimization/performance/metrics > before.json

# Apply optimization
POST /optimization/configure {...}

# Measure with new configuration
POST /optimization/performance/reset
# Run scenario...
GET /optimization/performance/metrics > after.json

# Compare results
```

## Performance Optimization Tips

### 1. Reduce Context Size

Large contexts slow down LLM calls:

```bash
# Use smaller context windows
{
  "max_turn_history": 5,  # Instead of 10
  "max_memories_per_entity": 5,  # Instead of 10
  "max_context_tokens": 2000  # Instead of 4000
}
```

### 2. Enable Caching

Context caching reduces repeated computation:

```bash
{
  "enable_caching": true
}
```

### 3. Use Optimization Presets

QuietStories includes presets for common scenarios:

```bash
# Fast preset for local LLMs
POST /optimization/presets/fast/apply

# Balanced preset for general use
POST /optimization/presets/balanced/apply

# Quality preset for maximum coherence
POST /optimization/presets/quality/apply
```

### 4. Monitor Memory Consolidation

Memory consolidation runs automatically every 10 turns. You can manually trigger it:

```python
# In your code
orchestrator.consolidate_session_memories()
```

### 5. Limit Tool Calls Per Turn

Configure the orchestrator to limit excessive tool usage:

```bash
# In config.py or .env
ORCHESTRATOR_RECURSION_LIMIT=50
```

## Interpreting Metrics

### LLM Call Latency

**Acceptable ranges** (varies by provider):
- **Local LLMs**: 1-5 seconds per call
- **OpenAI GPT-4**: 2-8 seconds per call
- **OpenAI GPT-3.5**: 0.5-2 seconds per call

**If too slow**:
- Reduce `max_context_tokens`
- Enable caching
- Use a faster model
- Reduce `max_turn_history`

### Tool Execution Time

**Acceptable ranges**:
- Individual tools: <100ms
- Batch of 5 tools: <500ms

**If too slow**:
- Check if tools are executing sequentially (should be parallel)
- Optimize database queries in memory tools
- Review custom tool implementations

### Turn Processing Time

**Acceptable ranges**:
- Simple turns: 2-5 seconds
- Complex turns with many tools: 5-15 seconds

**If too slow**:
- Review LLM call frequency
- Check tool execution count
- Optimize memory consolidation frequency

## Debugging Performance Issues

### Enable Verbose Logging

```bash
VERBOSE_ORCHESTRATOR=true
LOG_MESSAGE_SEQUENCES=true
```

This provides detailed logs for each operation:

```
[Verbose] Starting process_turn for session abc123
[Verbose] Built context with 8 keys
[Verbose] Optimized messages: 15 -> 12
[Verbose] About to call LLM provider...
[Verbose] LLM provider call completed
...
```

### Use the @time_it Decorator

Add timing to custom functions:

```python
from backend.utils.debug import time_it

@time_it
async def my_custom_function():
    # Your code here
    pass
```

### Monitor Specific Operations

```python
from backend.utils.debug import get_performance_metrics

metrics = get_performance_metrics()

# Start tracking
metrics.start_operation("my_operation", "llm_call")

# Your code here
await some_operation()

# End tracking
metrics.end_operation("my_operation", "llm_call", 
                     metadata={"custom": "data"})
```

## Advanced Optimization

### Custom Tool Batching

For custom scenarios, you can implement batching strategies:

```python
# Execute read-only tools first, then write tools
read_tools = [tool for tool in tools if tool.name in READ_ONLY_TOOLS]
write_tools = [tool for tool in tools if tool.name in WRITE_TOOLS]

# Execute in sequence: reads, then writes
# (LangGraph handles parallel execution within each batch)
```

### Async Tool Execution

Ensure custom tools are async for best performance:

```python
class MyTool(BaseTool):
    async def _arun(self, **kwargs):
        # Use async operations
        result = await async_operation()
        return result
```

## Monitoring in Production

### Grafana Integration

QuietStories can export metrics to Grafana. See [GRAFANA_INTEGRATION.md](GRAFANA_INTEGRATION.md) for setup.

### Log Analysis

Performance logs are structured for easy analysis:

```bash
# Find slow LLM calls (>5 seconds)
cat logs/app.log | grep "Performance" | grep "duration_ms" | \
  jq 'select(.duration_ms > 5000)'

# Calculate average tool execution time
cat logs/app.log | grep "tool_execution" | \
  jq '.duration_ms' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'
```

## Troubleshooting

### Problem: LLM calls taking >30 seconds

**Possible causes**:
- Context too large
- Network latency to provider
- Provider rate limiting

**Solutions**:
1. Reduce `max_context_tokens` to 2000
2. Check network connectivity
3. Review provider API status
4. Use a faster model

### Problem: Many tools executing sequentially

**Check**:
- ToolNode should handle parallel execution automatically
- Verify LangGraph is properly configured

**Solution**:
- Ensure using LangGraph 0.6.10+
- Check orchestrator graph construction

### Problem: Inconsistent performance

**Possible causes**:
- Varying context sizes
- Memory not being consolidated
- Cache misses

**Solutions**:
1. Enable context caching
2. Trigger manual memory consolidation
3. Monitor `max_turn_history` and `max_memories_per_entity`

## Summary

Key takeaways for optimal performance:

1. **Monitor metrics** using the performance API
2. **Use presets** for common scenarios
3. **Enable caching** to reduce repeated computation
4. **Limit context** to what's necessary
5. **Consolidate memory** regularly
6. **Review logs** to identify bottlenecks
7. **Tools execute in parallel** by default (LangGraph)

For further assistance, see:
- [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md) - Context optimization
- [LOGGING.md](LOGGING.md) - Logging configuration
- [GRAFANA_INTEGRATION.md](GRAFANA_INTEGRATION.md) - Production monitoring
