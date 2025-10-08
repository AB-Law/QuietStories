#!/usr/bin/env python3
"""
Examples of using debugging utilities in QuietStories

Run with:
    python debug_examples.py
"""

import asyncio
from src.utils.logger import setup_logging, get_logger
from src.utils.debug import (
    debug_point,
    debug_var,
    debug_state,
    time_it,
    trace_calls,
    debug_exception,
    compare_dicts,
    checkpoint,
    DebugSection,
    here,
    show
)

# Setup logging
setup_logging(level="DEBUG")
logger = get_logger(__name__)


# Example 1: Using debug_var
def example_debug_var():
    """Show how to use debug_var"""
    logger.info("\n=== Example 1: debug_var ===")
    
    my_dict = {"name": "Test Scenario", "turn": 5, "health": 100}
    my_list = [1, 2, 3, 4, 5]
    my_string = "Hello, World!"
    
    debug_var(my_dict, "my_dict")
    debug_var(my_list, "my_list")
    debug_var(my_string, "my_string")


# Example 2: Using conditional breakpoints
def example_conditional_breakpoint():
    """Show how to use debug_point"""
    logger.info("\n=== Example 2: Conditional Breakpoints ===")
    
    for i in range(10):
        logger.info(f"Processing item {i}")
        
        # Only break when i is 5
        # debug_point(i == 5, f"Reached i=5")
        
        # Uncomment above line to test breakpoint
        logger.info(f"Continuing with {i}")


# Example 3: Using time_it decorator
@time_it
async def slow_async_function():
    """Simulates a slow async operation"""
    await asyncio.sleep(0.5)
    return "Done"


@time_it
def slow_sync_function():
    """Simulates a slow sync operation"""
    import time
    time.sleep(0.3)
    return "Done"


async def example_time_it():
    """Show how to use time_it"""
    logger.info("\n=== Example 3: time_it Decorator ===")
    
    result1 = await slow_async_function()
    logger.info(f"Async result: {result1}")
    
    result2 = slow_sync_function()
    logger.info(f"Sync result: {result2}")


# Example 4: Using trace_calls decorator
@trace_calls
def calculate_something(x: int, y: int) -> int:
    """Example function with tracing"""
    result = x * y + x - y
    return result


@trace_calls
async def async_calculate(x: int, y: int) -> int:
    """Example async function with tracing"""
    await asyncio.sleep(0.1)
    return x + y


async def example_trace_calls():
    """Show how to use trace_calls"""
    logger.info("\n=== Example 4: trace_calls Decorator ===")
    
    result1 = calculate_something(5, 3)
    logger.info(f"Result: {result1}")
    
    result2 = await async_calculate(10, 20)
    logger.info(f"Async result: {result2}")


# Example 5: Using debug_state
def example_debug_state():
    """Show how to use debug_state"""
    logger.info("\n=== Example 5: debug_state ===")
    
    initial_state = {
        "player_health": 100,
        "player_location": "tavern",
        "inventory": ["sword", "shield"],
        "quest_completed": False
    }
    
    debug_state(initial_state, "Initial game state")
    
    # Simulate state change
    initial_state["player_health"] = 85
    initial_state["player_location"] = "forest"
    
    debug_state(initial_state, "After moving to forest")


# Example 6: Using debug_exception
def example_debug_exception():
    """Show how to use debug_exception"""
    logger.info("\n=== Example 6: debug_exception ===")
    
    try:
        # Simulate an error
        result = 10 / 0
    except Exception as e:
        debug_exception(e, "During calculation")
        logger.info("Continuing after exception...")


# Example 7: Using compare_dicts
def example_compare_dicts():
    """Show how to use compare_dicts"""
    logger.info("\n=== Example 7: compare_dicts ===")
    
    state_before = {
        "health": 100,
        "location": "tavern",
        "gold": 50,
        "level": 1
    }
    
    state_after = {
        "health": 85,  # Changed
        "location": "forest",  # Changed
        "gold": 50,  # Same
        "level": 1,  # Same
        "quest_log": ["Find the sword"]  # New key
    }
    
    compare_dicts(state_before, state_after, "before", "after")


# Example 8: Using checkpoint
def example_checkpoint():
    """Show how to use checkpoint"""
    logger.info("\n=== Example 8: checkpoint ===")
    
    checkpoint("start")
    
    data = {"step": 1}
    checkpoint("after_step_1", data)
    
    data["step"] = 2
    data["result"] = "success"
    checkpoint("after_step_2", data)


# Example 9: Using DebugSection context manager
def example_debug_section():
    """Show how to use DebugSection"""
    logger.info("\n=== Example 9: DebugSection ===")
    
    with DebugSection("Processing scenario"):
        logger.info("Doing some work...")
        import time
        time.sleep(0.2)
        logger.info("Work complete")
    
    try:
        with DebugSection("Risky operation"):
            logger.info("Starting risky work...")
            raise ValueError("Something went wrong!")
    except ValueError:
        logger.info("Handled the error")


# Example 10: Using here() for quick debugging
def example_here():
    """Show how to use here()"""
    logger.info("\n=== Example 10: here() ===")
    
    logger.info("Before the problematic code...")
    
    # Uncomment to test:
    # here("Check this spot")
    
    logger.info("After the problematic code...")


# Example 11: Using show() for quick variable inspection
def example_show():
    """Show how to use show()"""
    logger.info("\n=== Example 11: show() ===")
    
    name = "Test Scenario"
    turn = 5
    state = {"health": 100, "location": "tavern"}
    
    # Uncomment to test:
    # show(name, turn, state=state)


# Example 12: Real-world debugging scenario
@trace_calls
@time_it
async def simulate_turn_processing(session_id: str, action: str):
    """Simulate turn processing with debugging"""
    logger.info(f"\n=== Example 12: Real-world Scenario ===")
    
    checkpoint("turn_start", {"session_id": session_id, "action": action})
    
    # Simulate loading session
    with DebugSection("Loading session"):
        await asyncio.sleep(0.1)
        session_state = {
            "id": session_id,
            "turn": 5,
            "player_health": 100,
            "location": "tavern"
        }
        debug_state(session_state, "Session loaded")
    
    # Simulate processing
    with DebugSection("Processing action"):
        await asyncio.sleep(0.2)
        
        # Check for issues
        debug_point(
            session_state["player_health"] < 20,
            "Player health is low!"
        )
        
        # Update state
        old_state = session_state.copy()
        session_state["turn"] += 1
        session_state["player_health"] -= 10
        
        compare_dicts(old_state, session_state, "old_state", "new_state")
    
    checkpoint("turn_complete", {"new_turn": session_state["turn"]})
    
    return session_state


async def main():
    """Run all examples"""
    logger.info("="*60)
    logger.info("QuietStories Debugging Examples")
    logger.info("="*60)
    
    # Run examples
    example_debug_var()
    example_conditional_breakpoint()
    await example_time_it()
    await example_trace_calls()
    example_debug_state()
    
    try:
        example_debug_exception()
    except:
        pass
    
    example_compare_dicts()
    example_checkpoint()
    example_debug_section()
    example_here()
    example_show()
    
    # Real-world scenario
    result = await simulate_turn_processing("session-123", "explore")
    logger.info(f"\nFinal result: {result}")
    
    logger.info("\n" + "="*60)
    logger.info("Examples complete!")
    logger.info("="*60)
    logger.info("\nTo use these in your code:")
    logger.info("  from src.utils.debug import debug_var, debug_point, time_it")
    logger.info("  debug_var(my_variable, 'my_variable')")
    logger.info("  debug_point(condition, 'message')")
    logger.info("\nSee DEBUGGING_GUIDE.md for more information!")


if __name__ == "__main__":
    asyncio.run(main())
