"""
API endpoints for LLM optimization configuration and monitoring.

This module provides endpoints to:
- Configure optimization parameters
- Monitor optimization statistics
- Clear caches
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.utils.debug import get_performance_metrics
from backend.utils.logger import get_logger
from backend.utils.optimization import configure_optimizer, get_optimizer

logger = get_logger(__name__)

router = APIRouter()

# Configuration limits with rationale
# These values balance flexibility with preventing extreme configurations
MIN_CONTEXT_TOKENS = 1000  # Minimum for coherent responses
MAX_CONTEXT_TOKENS = 100000  # Maximum to prevent excessive API costs/timeouts
MIN_TURN_HISTORY = 1  # At least one turn for context
MAX_TURN_HISTORY = 50  # Beyond this, context becomes unwieldy
MIN_MEMORIES_PER_ENTITY = 1  # At least one memory to be useful
MAX_MEMORIES_PER_ENTITY = 100  # Practical limit for performance


class OptimizationConfig(BaseModel):
    """Configuration for LLM optimization"""

    max_turn_history: Optional[int] = Field(
        default=None,
        ge=MIN_TURN_HISTORY,
        le=MAX_TURN_HISTORY,
        description="Maximum turns to include in context history",
    )
    max_memories_per_entity: Optional[int] = Field(
        default=None,
        ge=MIN_MEMORIES_PER_ENTITY,
        le=MAX_MEMORIES_PER_ENTITY,
        description="Maximum memories per entity in context",
    )
    max_context_tokens: Optional[int] = Field(
        default=None,
        ge=MIN_CONTEXT_TOKENS,
        le=MAX_CONTEXT_TOKENS,
        description=f"Target maximum context size in tokens ({MIN_CONTEXT_TOKENS}-{MAX_CONTEXT_TOKENS})",
    )
    enable_caching: Optional[bool] = Field(
        default=None, description="Whether to enable context caching"
    )


class OptimizationStats(BaseModel):
    """Statistics about optimization performance"""

    cache_stats: Dict[str, Any]
    current_config: Dict[str, Any]


@router.get("/config")
async def get_optimization_config() -> Dict[str, Any]:
    """
    Get current optimization configuration.

    Returns:
        Current optimizer settings
    """
    logger.debug("Retrieving optimization configuration")

    optimizer = get_optimizer()

    return {
        "max_turn_history": optimizer.max_turn_history,
        "max_memories_per_entity": optimizer.max_memories_per_entity,
        "max_context_tokens": optimizer.max_context_tokens,
        "enable_caching": optimizer.enable_caching,
    }


@router.post("/config")
async def update_optimization_config(config: OptimizationConfig) -> Dict[str, Any]:
    """
    Update optimization configuration.

    Args:
        config: New optimization settings

    Returns:
        Updated configuration
    """
    logger.info(f"Updating optimization configuration: {config}")

    # Apply non-None values
    configure_optimizer(
        max_turn_history=config.max_turn_history,
        max_memories_per_entity=config.max_memories_per_entity,
        max_context_tokens=config.max_context_tokens,
        enable_caching=config.enable_caching,
    )

    # Return updated config
    optimizer = get_optimizer()

    updated_config = {
        "max_turn_history": optimizer.max_turn_history,
        "max_memories_per_entity": optimizer.max_memories_per_entity,
        "max_context_tokens": optimizer.max_context_tokens,
        "enable_caching": optimizer.enable_caching,
    }

    logger.info(f"✓ Optimization configuration updated")

    return updated_config


@router.get("/stats")
async def get_optimization_stats() -> OptimizationStats:
    """
    Get optimization performance statistics.

    Returns:
        Optimization statistics including cache performance
    """
    logger.debug("Retrieving optimization statistics")

    optimizer = get_optimizer()
    cache_stats = optimizer.cache.get_stats()

    current_config = {
        "max_turn_history": optimizer.max_turn_history,
        "max_memories_per_entity": optimizer.max_memories_per_entity,
        "max_context_tokens": optimizer.max_context_tokens,
        "enable_caching": optimizer.enable_caching,
    }

    return OptimizationStats(cache_stats=cache_stats, current_config=current_config)


@router.post("/cache/clear")
async def clear_optimization_cache() -> Dict[str, str]:
    """
    Clear all optimization caches.

    This will remove all cached context strings, forcing fresh computation.

    Returns:
        Success message
    """
    logger.info("Clearing optimization caches")

    optimizer = get_optimizer()
    optimizer.cache.clear()

    logger.info("✓ Optimization caches cleared")

    return {"status": "success", "message": "Optimization caches cleared"}


@router.get("/presets")
async def get_optimization_presets() -> Dict[str, Dict[str, Any]]:
    """
    Get predefined optimization presets for different use cases.

    Returns:
        Dictionary of preset configurations
    """
    return {
        "local_llm": {
            "description": "Optimized for local LLMs with limited context",
            "max_turn_history": 5,
            "max_memories_per_entity": 5,
            "max_context_tokens": 2000,
            "enable_caching": True,
        },
        "cloud_llm": {
            "description": "Optimized for cloud LLMs with large context windows",
            "max_turn_history": 15,
            "max_memories_per_entity": 15,
            "max_context_tokens": 8000,
            "enable_caching": True,
        },
        "minimal": {
            "description": "Minimal context for fastest processing",
            "max_turn_history": 3,
            "max_memories_per_entity": 3,
            "max_context_tokens": 1000,
            "enable_caching": True,
        },
        "maximum": {
            "description": "Maximum context for best quality (slowest)",
            "max_turn_history": 30,
            "max_memories_per_entity": 30,
            "max_context_tokens": 16000,
            "enable_caching": False,
        },
    }


@router.post("/presets/{preset_name}")
async def apply_optimization_preset(preset_name: str) -> Dict[str, Any]:
    """
    Apply a predefined optimization preset.

    Args:
        preset_name: Name of preset to apply (local_llm, cloud_llm, minimal, maximum)

    Returns:
        Applied configuration
    """
    logger.info(f"Applying optimization preset: {preset_name}")

    presets = await get_optimization_presets()

    if preset_name not in presets:
        return {
            "status": "error",
            "message": f"Unknown preset: {preset_name}",
            "available_presets": list(presets.keys()),
        }

    preset = presets[preset_name]

    # Apply preset configuration
    configure_optimizer(
        max_turn_history=preset["max_turn_history"],
        max_memories_per_entity=preset["max_memories_per_entity"],
        max_context_tokens=preset["max_context_tokens"],
        enable_caching=preset["enable_caching"],
    )

    logger.info(f"✓ Applied preset: {preset_name}")

    return {
        "status": "success",
        "preset": preset_name,
        "description": preset["description"],
        "config": {k: v for k, v in preset.items() if k != "description"},
    }


@router.get("/performance/metrics")
async def get_performance_metrics_endpoint() -> Dict[str, Any]:
    """
    Get comprehensive performance metrics for LLM calls and tool execution.

    This endpoint provides insights into:
    - LLM call latencies and patterns
    - Tool execution times
    - Turn processing durations
    - Performance bottlenecks

    Returns:
        Performance metrics summary with statistics
    """
    logger.debug("Retrieving performance metrics")

    metrics = get_performance_metrics()
    summary = metrics.get_summary()

    return {
        "status": "success",
        "metrics": summary,
        "description": "Performance metrics for LLM calls, tool executions, and turn processing",
    }


@router.post("/performance/reset")
async def reset_performance_metrics() -> Dict[str, str]:
    """
    Reset all performance metrics.

    Useful for starting fresh measurements after configuration changes
    or to analyze specific scenarios.

    Returns:
        Success message
    """
    logger.info("Resetting performance metrics")

    metrics = get_performance_metrics()
    metrics.reset()

    logger.info("✓ Performance metrics reset")

    return {
        "status": "success",
        "message": "Performance metrics have been reset",
    }
