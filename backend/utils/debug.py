"""
Debug utilities for QuietStories

Provides helpful debugging functions and decorators.

Usage:
    from backend.utils.debug import debug_point, debug_var, time_it, trace_calls

    # Quick debug print
    debug_var(my_variable, "my_variable")

    # Conditional breakpoint
    debug_point(condition=some_value > 10, message="Value too high")

    # Time a function
    @time_it
    def slow_function():
        ...

    # Trace all function calls
    @trace_calls
    def complex_function():
        ...
"""

import functools
import json
import sys
import time
import traceback
from typing import Any, Callable, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def debug_point(condition: bool = True, message: str = "Debug breakpoint"):
    """
    Conditional breakpoint with message

    Args:
        condition: Break only if this is True
        message: Message to display when breaking

    Example:
        debug_point(user_id is None, "User ID is None!")
        debug_point(len(items) > 100, "Too many items")
    """
    if condition:
        logger.warning(f"🔴 {message}")
        breakpoint()


def debug_var(var: Any, name: str = "variable", pretty: bool = True):
    """
    Pretty print a variable for debugging

    Args:
        var: Variable to print
        name: Name of the variable
        pretty: Use pretty printing

    Example:
        debug_var(scenario_spec, "scenario_spec")
        debug_var(state, "current_state")
    """
    logger.debug(f"📍 Debug: {name}")
    logger.debug(f"  Type: {type(var).__name__}")

    try:
        if hasattr(var, "dict"):
            # Pydantic model
            content = var.dict()
        elif hasattr(var, "__dict__"):
            # Object with __dict__
            content = var.__dict__
        else:
            content = var

        if pretty and isinstance(content, (dict, list)):
            formatted = json.dumps(content, indent=2, default=str)
            logger.debug(f"  Value:\n{formatted}")
        else:
            logger.debug(f"  Value: {content}")
    except Exception as e:
        logger.debug(f"  Value: {repr(var)}")
        logger.debug(f"  (Could not format: {e})")


def debug_state(state: dict, message: str = "Current State"):
    """
    Debug helper for state dictionaries

    Args:
        state: State dictionary to debug
        message: Message to display

    Example:
        debug_state(session['state'], "After turn processing")
    """
    logger.debug(f"🔍 {message}")
    logger.debug(f"  Keys: {list(state.keys())}")
    logger.debug(f"  Size: {len(state)} items")

    if state:
        logger.debug("  Contents:")
        for key, value in list(state.items())[:10]:  # First 10 items
            value_str = str(value)[:100]  # Truncate long values
            logger.debug(f"    {key}: {value_str}")

        if len(state) > 10:
            logger.debug(f"    ... and {len(state) - 10} more items")


def time_it(func: Callable) -> Callable:
    """
    Decorator to time function execution

    Example:
        @time_it
        def slow_function():
            time.sleep(1)
            return "done"

        result = slow_function()
        # Logs: "slow_function took 1.00 seconds"
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"⏱️  {func.__name__} took {elapsed:.2f} seconds")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"⏱️  {func.__name__} failed after {elapsed:.2f} seconds: {e}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"⏱️  {func.__name__} took {elapsed:.2f} seconds")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"⏱️  {func.__name__} failed after {elapsed:.2f} seconds: {e}")
            raise

    # Return appropriate wrapper based on whether function is async
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def trace_calls(func: Callable) -> Callable:
    """
    Decorator to trace function calls and returns

    Example:
        @trace_calls
        def calculate(x, y):
            return x + y

        result = calculate(2, 3)
        # Logs: "→ calculate(2, 3)"
        # Logs: "← calculate returned 5"
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        args_repr = [repr(a)[:50] for a in args[:3]]  # First 3 args
        kwargs_repr = [f"{k}={repr(v)[:50]}" for k, v in list(kwargs.items())[:3]]
        signature = ", ".join(args_repr + kwargs_repr)

        logger.debug(f"→ {func.__name__}({signature})")

        try:
            result = await func(*args, **kwargs)
            result_repr = repr(result)[:100]
            logger.debug(f"← {func.__name__} returned {result_repr}")
            return result
        except Exception as e:
            logger.error(f"✗ {func.__name__} raised {type(e).__name__}: {e}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        args_repr = [repr(a)[:50] for a in args[:3]]
        kwargs_repr = [f"{k}={repr(v)[:50]}" for k, v in list(kwargs.items())[:3]]
        signature = ", ".join(args_repr + kwargs_repr)

        logger.debug(f"→ {func.__name__}({signature})")

        try:
            result = func(*args, **kwargs)
            result_repr = repr(result)[:100]
            logger.debug(f"← {func.__name__} returned {result_repr}")
            return result
        except Exception as e:
            logger.error(f"✗ {func.__name__} raised {type(e).__name__}: {e}")
            raise

    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def debug_exception(e: Exception, context: str = ""):
    """
    Debug helper for exceptions with full context

    Args:
        e: Exception to debug
        context: Additional context message

    Example:
        try:
            risky_operation()
        except Exception as e:
            debug_exception(e, "During scenario generation")
            raise
    """
    logger.error(f"🔥 Exception caught{' in ' + context if context else ''}")
    logger.error(f"  Type: {type(e).__name__}")
    logger.error(f"  Message: {str(e)}")
    logger.error(f"  Traceback:")

    # Get and log full traceback
    tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
    for line in tb_lines:
        for subline in line.rstrip().split("\n"):
            logger.error(f"    {subline}")


def compare_dicts(dict1: dict, dict2: dict, name1: str = "dict1", name2: str = "dict2"):
    """
    Compare two dictionaries and show differences

    Args:
        dict1: First dictionary
        dict2: Second dictionary
        name1: Name for first dict
        name2: Name for second dict

    Example:
        compare_dicts(state_before, state_after, "before", "after")
    """
    logger.debug(f"📊 Comparing {name1} vs {name2}")

    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    # Keys only in dict1
    only_in_1 = keys1 - keys2
    if only_in_1:
        logger.debug(f"  Keys only in {name1}: {only_in_1}")

    # Keys only in dict2
    only_in_2 = keys2 - keys1
    if only_in_2:
        logger.debug(f"  Keys only in {name2}: {only_in_2}")

    # Common keys with different values
    common_keys = keys1 & keys2
    differences = []
    for key in common_keys:
        if dict1[key] != dict2[key]:
            differences.append(key)
            val1_str = str(dict1[key])[:50]
            val2_str = str(dict2[key])[:50]
            logger.debug(f"  {key}: {val1_str} → {val2_str}")

    if not only_in_1 and not only_in_2 and not differences:
        logger.debug("  ✓ Dictionaries are identical")


def checkpoint(name: str, data: Optional[dict] = None):
    """
    Create a named checkpoint for debugging

    Args:
        name: Name of the checkpoint
        data: Optional data to log at checkpoint

    Example:
        checkpoint("before_generation")
        result = generate_scenario()
        checkpoint("after_generation", {"result": result})
    """
    logger.info(f"🚩 Checkpoint: {name}")

    if data:
        logger.debug(f"  Data at checkpoint:")
        for key, value in data.items():
            value_str = str(value)[:100]
            logger.debug(f"    {key}: {value_str}")


def watch_value(
    getter: Callable,
    name: str,
    interval: float = 1.0,
    condition: Optional[Callable] = None,
):
    """
    Watch a value and break when condition is met

    Args:
        getter: Function that returns the value to watch
        name: Name of the value
        interval: How often to check (seconds)
        condition: Optional condition function, breaks when it returns True

    Example:
        def check_session():
            return sessions_db['abc-123']

        watch_value(check_session, "session", condition=lambda s: s['turn'] > 5)
    """
    logger.debug(f"👁️  Watching {name}")

    while True:
        try:
            value = getter()
            logger.debug(f"  {name} = {value}")

            if condition and condition(value):
                logger.warning(f"🔔 Watch condition met for {name}")
                breakpoint()
                break

            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info(f"Stopped watching {name}")
            break
        except Exception as e:
            logger.error(f"Error watching {name}: {e}")
            break


# Context manager for debugging sections
class DebugSection:
    """
    Context manager for debugging a section of code

    Example:
        with DebugSection("Turn processing"):
            result = process_turn(session_id, action)
        # Automatically logs entry/exit and timing
    """

    def __init__(
        self, name: str, break_on_entry: bool = False, break_on_exit: bool = False
    ):
        self.name = name
        self.break_on_entry = break_on_entry
        self.break_on_exit = break_on_exit
        self.start_time = None

    def __enter__(self):
        logger.debug(f"▶️  Entering: {self.name}")
        self.start_time = time.time()

        if self.break_on_entry:
            logger.warning(f"🔴 Breaking at entry of: {self.name}")
            breakpoint()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time

        if exc_type is not None:
            logger.error(
                f"❌ {self.name} failed after {elapsed:.2f}s: {exc_type.__name__}"
            )
        else:
            logger.debug(f"✅ {self.name} completed in {elapsed:.2f}s")

        if self.break_on_exit:
            logger.warning(f"🔴 Breaking at exit of: {self.name}")
            breakpoint()

        return False  # Don't suppress exceptions


# Quick access to common debugging patterns
def here(message: str = "HERE"):
    """Quick debug marker - prints and breaks"""
    logger.warning(f"🔴 {message}")
    breakpoint()


def show(*args, **kwargs):
    """Quick debug print with breakpoint"""
    for i, arg in enumerate(args):
        debug_var(arg, f"arg{i}")
    for key, value in kwargs.items():
        debug_var(value, key)
    breakpoint()
