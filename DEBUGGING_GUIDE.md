# Python Debugging Guide for QuietStories

This guide covers various debugging techniques and tools you can use with your Python scripts.

## Table of Contents
- [Quick Start](#quick-start)
- [Built-in Python Debugger (pdb)](#built-in-python-debugger-pdb)
- [Enhanced Debugger (ipdb)](#enhanced-debugger-ipdb)
- [VSCode Debugging](#vscode-debugging)
- [Debugging with Logging](#debugging-with-logging)
- [Debugging API Calls](#debugging-api-calls)
- [Common Debugging Scenarios](#common-debugging-scenarios)

---

## Quick Start

### Method 1: Using `breakpoint()` (Recommended for Python 3.7+)

Simply add `breakpoint()` anywhere in your code:

```python
async def generate_scenario(request: ScenarioGenerateRequest):
    logger.info("Starting scenario generation...")
    
    # Add a breakpoint here
    breakpoint()
    
    generator = ScenarioGenerator()
    scenario_spec = await generator.generate_scenario(request.description)
    return scenario_spec
```

Then run your script normally - execution will pause at the breakpoint!

### Method 2: Using `pdb.set_trace()`

```python
import pdb

async def generate_scenario(request: ScenarioGenerateRequest):
    logger.info("Starting scenario generation...")
    
    # Add a breakpoint here
    pdb.set_trace()
    
    generator = ScenarioGenerator()
    scenario_spec = await generator.generate_scenario(request.description)
    return scenario_spec
```

---

## Built-in Python Debugger (pdb)

### Basic Usage

```python
# Import pdb
import pdb

# Set a breakpoint
pdb.set_trace()

# Or use the built-in function (Python 3.7+)
breakpoint()
```

### Essential pdb Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| `help` | `h` | Show help |
| `continue` | `c` | Continue execution until next breakpoint |
| `next` | `n` | Execute next line (don't step into functions) |
| `step` | `s` | Step into function |
| `return` | `r` | Continue until current function returns |
| `list` | `l` | Show source code around current line |
| `print <expr>` | `p <expr>` | Print value of expression |
| `pp <expr>` | | Pretty-print value of expression |
| `where` | `w` | Show stack trace |
| `up` | `u` | Move up one stack frame |
| `down` | `d` | Move down one stack frame |
| `break <location>` | `b <location>` | Set a breakpoint |
| `clear` | `cl` | Clear breakpoints |
| `quit` | `q` | Exit debugger |

### Example Session

```python
# In your code
def process_turn(session_id: str, action: str):
    breakpoint()  # Execution pauses here
    
    session = sessions_db[session_id]
    orchestrator = orchestrators_db[session_id]
    outcome = orchestrator.process_turn(action)
    return outcome
```

When execution pauses:
```
> /path/to/file.py(123)process_turn()
-> session = sessions_db[session_id]

(Pdb) p session_id
'abc-123-xyz'

(Pdb) p sessions_db.keys()
dict_keys(['abc-123-xyz', 'def-456-uvw'])

(Pdb) n
> /path/to/file.py(124)process_turn()
-> orchestrator = orchestrators_db[session_id]

(Pdb) l
119     def process_turn(session_id: str, action: str):
120         breakpoint()
121         
122         session = sessions_db[session_id]
123         orchestrator = orchestrators_db[session_id]
124  ->     outcome = orchestrator.process_turn(action)
125         return outcome

(Pdb) c
```

---

## Enhanced Debugger (ipdb)

`ipdb` is like `pdb` but with syntax highlighting, tab completion, and better formatting.

### Installation

```bash
pip install ipdb
```

### Usage

```python
import ipdb

# Set a breakpoint
ipdb.set_trace()

# Or configure breakpoint() to use ipdb
# Add to your .bashrc or .zshrc:
# export PYTHONBREAKPOINT=ipdb.set_trace
```

### Features

- ✨ Syntax highlighting
- ✨ Tab completion
- ✨ Better object inspection
- ✨ All pdb commands work

---

## VSCode Debugging

### Setup

1. Create `.vscode/launch.json` in your project root:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI App",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": false,
            "env": {
                "LOG_LEVEL": "DEBUG"
            }
        },
        {
            "name": "Python: API Test Script",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/api_test.py",
            "args": [
                "workflow",
                "A fantasy adventure",
                "--log-level", "DEBUG"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Python: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Python: Debug Tests",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "-v",
                "-s",
                "${file}"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

### Usage

1. Set breakpoints by clicking left of line numbers (red dot appears)
2. Press F5 or Run → Start Debugging
3. Use the debug toolbar to step through code
4. Hover over variables to see their values
5. Use Debug Console to evaluate expressions

### VSCode Debug Shortcuts

| Shortcut | Action |
|----------|--------|
| `F5` | Start/Continue |
| `F10` | Step Over |
| `F11` | Step Into |
| `Shift+F11` | Step Out |
| `Ctrl+Shift+F5` | Restart |
| `Shift+F5` | Stop |

---

## Debugging with Logging

You can use the new logging system for debugging without stopping execution:

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def generate_scenario(description: str):
    logger.debug(f"Input description: {description}")
    
    generator = ScenarioGenerator()
    logger.debug(f"Generator provider: {generator.provider}")
    
    result = await generator.generate_scenario(description)
    logger.debug(f"Result type: {type(result)}")
    logger.debug(f"Result attributes: {dir(result)}")
    
    return result
```

Run with DEBUG level to see all debug messages:
```bash
LOG_LEVEL=DEBUG python api_test.py generate "test"
```

---

## Debugging API Calls

### Method 1: Debug API Functions Directly

Use the `api_test.py` script with a debugger:

```python
# In api_test.py, add breakpoint before the test
async def test_generate_scenario(self, description: str):
    breakpoint()  # Add this
    request = ScenarioGenerateRequest(description=description)
    result = await generate_scenario(request)
    return result
```

Then run:
```bash
python api_test.py generate "A fantasy story"
```

### Method 2: Debug While Server is Running

Add breakpoints in your API code:

```python
# In src/api/scenarios.py
@router.post("/generate")
async def generate_scenario(request: ScenarioGenerateRequest):
    breakpoint()  # Debugger will pause when endpoint is called
    
    generator = ScenarioGenerator()
    scenario_spec = await generator.generate_scenario(request.description)
    return scenario_spec
```

Run server with debugger:
```bash
python -m pdb -m uvicorn src.main:app --reload
```

Or in VSCode, use the "Python: FastAPI App" debug configuration.

### Method 3: Remote Debugging

For debugging running containers or remote servers:

```bash
pip install debugpy
```

Add to your code:
```python
import debugpy

# Wait for debugger to attach
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger attach...")
debugpy.wait_for_client()
print("Debugger attached!")
```

---

## Common Debugging Scenarios

### Scenario 1: Debug Scenario Generation

```python
# In src/engine/generator.py
async def generate_scenario(self, description: str) -> ScenarioSpec:
    logger.info(f"Generating scenario from: {description}")
    
    # Debug: Check prompt construction
    breakpoint()
    system_prompt = SCENARIO_GENERATION_SYSTEM
    user_prompt = SCENARIO_GENERATION_USER.format(description=description)
    
    # Debug: Check LLM response
    response = await self.provider.chat(messages, max_tokens=4000)
    breakpoint()
    
    # Debug: Check parsing
    parsed = self._parse_scenario_json(response.content)
    breakpoint()
    
    return parsed
```

Run:
```bash
python api_test.py generate "A mystery story" --log-level DEBUG
```

### Scenario 2: Debug Turn Processing

```python
# In src/engine/orchestrator.py
async def process_turn(self, action: Optional[str] = None) -> Outcome:
    logger.info(f"Processing turn with action: {action}")
    
    # Debug: Check current state
    breakpoint()
    current_state = self.spec.state
    logger.debug(f"Current state: {current_state}")
    
    # Debug: Check available actions
    available_actions = self._get_available_actions()
    breakpoint()
    
    # Debug: Check outcome
    outcome = await self._generate_outcome(action, available_actions)
    breakpoint()
    
    return outcome
```

### Scenario 3: Debug State Changes

```python
# In src/engine/compiler.py
def apply_state_changes(state: Dict, changes: List[StateChange]) -> Dict:
    logger.debug(f"Applying {len(changes)} state changes")
    
    # Debug before changes
    breakpoint()
    logger.debug(f"State before: {state}")
    
    for change in changes:
        # Debug each change
        logger.debug(f"Applying: {change}")
        state = apply_change(state, change)
        breakpoint()  # Pause after each change
    
    # Debug after changes
    logger.debug(f"State after: {state}")
    breakpoint()
    
    return state
```

### Scenario 4: Debug Async Functions

For async functions, use regular breakpoints - they work with asyncio:

```python
async def async_function():
    result = await some_async_call()
    breakpoint()  # This works!
    return result
```

### Scenario 5: Debug LLM Responses

```python
# In src/providers/base.py
async def chat(self, messages, **kwargs):
    logger.debug(f"Sending messages to LLM: {messages}")
    
    response = await self.llm.ainvoke(messages)
    
    # Debug: Inspect response
    breakpoint()
    logger.debug(f"Response type: {type(response)}")
    logger.debug(f"Response content: {response.content}")
    logger.debug(f"Response metadata: {response.response_metadata}")
    
    return response
```

---

## Debugging Tips

### 1. Conditional Breakpoints

```python
# Only break when condition is true
if some_condition:
    breakpoint()

# Or use pdb conditionally
import pdb; pdb.set_trace() if session_id == "abc" else None
```

### 2. Post-Mortem Debugging

If your program crashes, you can debug it:

```python
import pdb

try:
    result = risky_operation()
except Exception:
    pdb.post_mortem()  # Debug at the point of failure
```

Or run with automatic post-mortem:
```bash
python -m pdb -c continue api_test.py generate "test"
```

### 3. Debug Specific Module

```python
# Add to your script
import sys
sys.settrace(lambda *args: None)  # Disable tracing

# Later, enable for specific section
import pdb
pdb.set_trace()
```

### 4. Pretty Print Complex Objects

```python
# In debugger
(Pdb) import json
(Pdb) print(json.dumps(scenario_spec.dict(), indent=2))

# Or use pp
(Pdb) pp scenario_spec.__dict__
```

### 5. Inspect Variables

```python
# In debugger
(Pdb) locals()  # All local variables
(Pdb) globals()  # All global variables
(Pdb) dir(obj)  # Object attributes
(Pdb) type(obj)  # Object type
(Pdb) vars(obj)  # Object __dict__
```

---

## Debugging Checklist

When debugging an issue:

- [ ] Set LOG_LEVEL=DEBUG
- [ ] Add strategic breakpoints
- [ ] Check input values
- [ ] Step through logic
- [ ] Inspect intermediate values
- [ ] Check for None/empty values
- [ ] Verify type conversions
- [ ] Check error messages
- [ ] Review stack trace
- [ ] Test with simple inputs first

---

## Troubleshooting

### Breakpoint Not Stopping?

1. Make sure code is actually executing
2. Check if breakpoint is in dead code
3. Try adding print statement before breakpoint
4. Use conditional breakpoint for specific cases

### Can't See Variables?

1. Move up/down stack frames with `u`/`d`
2. Use `where` to see current position
3. Use `locals()` to see all local variables
4. Check variable scope

### Async Debugging Issues?

1. Use `await` in debugger for async calls
2. Use `asyncio.run()` for testing async functions
3. Add `import asyncio` in debugger if needed

### VSCode Debugger Not Working?

1. Install `debugpy`: `pip install debugpy`
2. Check launch.json configuration
3. Set "justMyCode": false to debug library code
4. Restart VSCode

---

## Quick Reference Card

```python
# Start debugging
breakpoint()                    # Python 3.7+
import pdb; pdb.set_trace()    # Python 2.7+
import ipdb; ipdb.set_trace()  # Enhanced debugger

# Navigation
n, next      # Next line
s, step      # Step into
r, return    # Return from function
c, continue  # Continue execution
q, quit      # Quit debugger

# Inspection
p expr       # Print expression
pp expr      # Pretty print
l, list      # Show code
w, where     # Show stack
a, args      # Show function arguments

# Breakpoints
b line_num   # Set breakpoint at line
b func       # Set breakpoint at function
cl           # Clear all breakpoints
disable N    # Disable breakpoint N
enable N     # Enable breakpoint N

# Stack
u, up        # Move up stack
d, down      # Move down stack
bt           # Backtrace

# Execution
!expr        # Execute Python expression
interact     # Start interactive interpreter
```

---

## Additional Resources

- [Python pdb documentation](https://docs.python.org/3/library/pdb.html)
- [ipdb GitHub](https://github.com/gotcha/ipdb)
- [VSCode Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [Real Python pdb guide](https://realpython.com/python-debugging-pdb/)

---

Happy Debugging! 🐛🔍
