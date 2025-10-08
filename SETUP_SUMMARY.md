# QuietStories - Logging, Testing & Debugging Setup Summary

## What's Been Added

I've set up a comprehensive logging, testing, and debugging system for your QuietStories project. Here's everything that was added:

## 📁 New Files Created

### 1. Logging System
- **`src/utils/logger.py`** - Centralized logging with color-coded output, multiple verbosity levels
- **Enhanced all API files** with detailed logging (scenarios.py, sessions.py, prompts.py, main.py)

### 2. Testing Infrastructure  
- **`api_test.py`** - HTTP-based API testing script (makes real requests to your server)
- **`API_TESTING_GUIDE.md`** - Complete guide for testing your APIs

### 3. Debugging Tools
- **`src/utils/debug.py`** - Debugging utilities (breakpoints, timers, tracers, etc.)
- **`debug_examples.py`** - Runnable examples of all debugging utilities
- **`DEBUGGING_GUIDE.md`** - Comprehensive debugging reference (614 lines!)
- **`.vscode/launch.json`** - VSCode/Cursor debug configurations

## 🎯 Key Features

### Logging System

**Verbosity Levels:**
- `DEBUG` - Detailed information for diagnosing problems
- `INFO` - General informational messages (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages for serious problems
- `CRITICAL` - Critical messages for very serious errors

**Features:**
- ✨ Color-coded console output
- ✨ Structured logging with timestamps
- ✨ Optional file logging
- ✨ Module-level log control
- ✨ Automatic noise filtering for libraries

**Usage:**
```bash
# Set log level via environment variable
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload

# Or with log file
LOG_LEVEL=DEBUG LOG_FILE=logs/app.log python -m uvicorn src.main:app --reload
```

### API Testing Script

**`api_test.py` now makes HTTP requests to your running server!**

**Usage:**
```bash
# Start server first (Terminal 1)
python -m uvicorn src.main:app --reload

# Or press F5 in VSCode/Cursor for debug mode

# Then run tests (Terminal 2)
python api_test.py generate "A fantasy adventure"
python api_test.py workflow "Complete test"
python api_test.py list-scenarios
```

**Commands Available:**
- `enrich` - Test prompt enrichment
- `generate` - Test scenario generation  
- `compile` - Test scenario compilation
- `create-session` - Create a session
- `process-turn` - Process a turn
- `workflow` - Test complete workflow
- `list-scenarios` - List all scenarios
- `list-sessions` - List all sessions
- `get-scenario` - Get specific scenario
- `get-session` - Get specific session

**Options:**
- `--url` - Custom server URL (default: http://localhost:8000)
- `--log-level` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `--log-file` - Save logs to file
- `--action` - Action for turn processing
- `--seed` - Seed for session creation
- `--max-tokens` - Max tokens for enrichment

### Debugging Utilities

**In `src/utils/debug.py`:**

```python
from src.utils.debug import (
    debug_var,      # Pretty print variables
    debug_point,    # Conditional breakpoints
    debug_state,    # Debug state dictionaries
    time_it,        # Time function execution
    trace_calls,    # Trace function calls
    debug_exception,# Debug exceptions with context
    compare_dicts,  # Compare two dictionaries
    checkpoint,     # Create named checkpoints
    DebugSection,   # Context manager for debugging sections
    here,          # Quick debug marker
    show           # Quick variable inspection
)
```

**Examples:**
```python
# Quick variable inspection
debug_var(scenario_spec, "scenario_spec")

# Conditional breakpoint
debug_point(health < 20, "Player health is low!")

# Time a function
@time_it
async def slow_function():
    await asyncio.sleep(1)

# Trace function calls
@trace_calls
def my_function(x, y):
    return x + y

# Debug a section
with DebugSection("Turn processing"):
    result = process_turn()
```

### VSCode/Cursor Debug Configurations

**Press F5 and choose:**

1. **FastAPI: Run Server** - Debug mode with DEBUG logging
2. **FastAPI: Run Server (INFO logging)** - Debug mode with INFO logging
3. **API Test: Full Workflow** - Debug the workflow test
4. **API Test: Generate Scenario** - Debug scenario generation
5. **API Test: Enrich Prompt** - Debug prompt enrichment
6. **Python: Current File** - Debug current file
7. **Python: Debug Tests** - Debug pytest tests

## 🚀 How to Use Everything

### For Normal Development

```bash
# Terminal 1: Start server with INFO logging
LOG_LEVEL=INFO python -m uvicorn src.main:app --reload

# Terminal 2: Test your APIs
python api_test.py workflow "A fantasy adventure"
```

### For Debugging Issues

```bash
# Method 1: VSCode Debugging (Recommended)
1. Open your API file (e.g., src/api/scenarios.py)
2. Click left of line numbers to set breakpoints (red dots)
3. Press F5, select "FastAPI: Run Server"
4. In separate terminal: python api_test.py generate "test"
5. Execution pauses at breakpoints!

# Method 2: Command Line with DEBUG logging
# Terminal 1
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload

# Terminal 2
python api_test.py generate "test" --log-level DEBUG
```

### For Detailed Analysis

```bash
# Save logs to file for analysis
python api_test.py workflow "complex scenario" \
  --log-level DEBUG \
  --log-file logs/workflow-$(date +%Y%m%d-%H%M%S).log

# Then review the log file
cat logs/workflow-*.log | grep ERROR
```

## 📚 Documentation

All documentation is included:

- **`API_TESTING_GUIDE.md`** - How to test your APIs with the new HTTP-based script
- **`DEBUGGING_GUIDE.md`** - Complete debugging reference with techniques and examples
- **`SETUP_SUMMARY.md`** - This file!

## 🔍 Example: Debugging Scenario Generation

### 1. Set Breakpoint

Open `src/api/scenarios.py` and click left of line 59 to set a breakpoint:

```python
59|  generator = ScenarioGenerator()  # ← Click here
```

### 2. Start Debugging

Press `F5` in Cursor/VSCode, select "FastAPI: Run Server"

### 3. Trigger API

In separate terminal:
```bash
python api_test.py generate "A fantasy adventure" --log-level DEBUG
```

### 4. Debug

When execution pauses:
- **Variables panel** shows all local variables
- **Hover** over variables to see values
- **Debug Console** to evaluate expressions:
  ```python
  request.description
  generator.provider.__class__.__name__
  ```
- **Step through** with F10 (step over) or F11 (step into)

### 5. Review Output

The test script shows:
```
============================================================
GENERATED SCENARIO:
------------------------------------------------------------
ID: abc-123-xyz
Name: The Fantasy Adventure
Spec Version: 1.0
Status: generated
============================================================
```

## 🎨 Log Output Examples

### INFO Level (Normal Operation)
```
2025-10-08 14:23:45 | INFO     | src.api.scenarios | ============================================================
2025-10-08 14:23:45 | INFO     | src.api.scenarios | SCENARIO GENERATION REQUEST
2025-10-08 14:23:45 | INFO     | src.api.scenarios | Description: A fantasy adventure...
2025-10-08 14:23:45 | INFO     | src.api.scenarios | Starting scenario generation...
2025-10-08 14:23:47 | INFO     | src.api.scenarios | ✓ Scenario generated successfully: The Fantasy Adventure
```

### DEBUG Level (Detailed)
```
2025-10-08 14:23:45 | DEBUG    | src.api.scenarios | Full description: A fantasy adventure with dragons and magic
2025-10-08 14:23:45 | DEBUG    | src.api.scenarios | Initializing ScenarioGenerator...
2025-10-08 14:23:45 | DEBUG    | src.api.scenarios | Generator created with provider: OpenAIProvider
2025-10-08 14:23:47 | DEBUG    | src.api.scenarios | Spec version: 1.0
2025-10-08 14:23:47 | DEBUG    | src.api.scenarios | Number of actions: 5
2025-10-08 14:23:47 | DEBUG    | src.api.scenarios | Number of locations: 3
```

## 🛠️ Quick Reference

### Starting the Server

```bash
# Normal mode
python -m uvicorn src.main:app --reload

# With DEBUG logging
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload

# With file logging
LOG_LEVEL=DEBUG LOG_FILE=logs/server.log python -m uvicorn src.main:app --reload

# Debug mode in VSCode
Press F5 → Select "FastAPI: Run Server"
```

### Running Tests

```bash
# Single command
python api_test.py <command> <arg> [options]

# Examples
python api_test.py generate "test"
python api_test.py workflow "full test" --log-level DEBUG
python api_test.py list-scenarios
python api_test.py compile scenario-id --log-level INFO
```

### Setting Log Levels

```bash
# Environment variable (for server)
export LOG_LEVEL=DEBUG

# Command line flag (for test script)
python api_test.py generate "test" --log-level DEBUG

# Both together
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload &
python api_test.py workflow "test" --log-level DEBUG
```

### Debug Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F5` | Start/Continue |
| `F9` | Toggle breakpoint |
| `F10` | Step over |
| `F11` | Step into |
| `Shift+F11` | Step out |
| `Cmd+Shift+F5` | Restart |
| `Shift+F5` | Stop |

## 📦 What Changed in Existing Files

### API Files (`src/api/*.py`)
- Replaced `logging.basicConfig()` with `get_logger(__name__)`
- Added detailed debug logging
- Added structured log messages with ✓, ✗, ⚠ symbols
- Added request/response logging
- Added state change logging

### Main Application (`src/main.py`)
- Added logging initialization
- Added LOG_LEVEL environment variable support
- Added LOG_FILE environment variable support
- Added server configuration logging

### Config (`src/config.py`)
- No changes needed (already had settings)

## 🎯 Benefits

### Before
- ❌ Basic logging with no structure
- ❌ Test script called functions directly
- ❌ No debugging configurations
- ❌ Hard to trace issues
- ❌ No visibility into what's happening

### After
- ✅ Structured, color-coded logging with multiple levels
- ✅ HTTP-based testing (tests full stack)
- ✅ VSCode debug configurations ready to use
- ✅ Debugging utilities for quick inspection
- ✅ Full visibility with detailed logs
- ✅ Easy to set breakpoints and debug
- ✅ Comprehensive documentation

## 🚦 Next Steps

1. **Try it out:**
   ```bash
   # Terminal 1
   python -m uvicorn src.main:app --reload
   
   # Terminal 2
   python api_test.py workflow "A fantasy adventure"
   ```

2. **Set a breakpoint:**
   - Open `src/api/scenarios.py`
   - Click left of line 59
   - Press F5 to start debugging
   - Run a test

3. **Explore the utilities:**
   ```bash
   python debug_examples.py
   ```

4. **Read the guides:**
   - `API_TESTING_GUIDE.md` - Testing reference
   - `DEBUGGING_GUIDE.md` - Debugging reference

## 💡 Pro Tips

1. **Use two terminals** - Server in one, tests in another
2. **Start with INFO** level, use DEBUG when you need details
3. **Set breakpoints** in VSCode instead of adding print statements
4. **Save logs to files** for complex issues
5. **Use the debug utilities** (`debug_var`, `debug_state`, etc.) for quick inspection
6. **Run debug_examples.py** to see all features in action

## 🆘 Troubleshooting

### Server won't start
```bash
# Check if port is already in use
lsof -i :8000

# Kill existing process
kill -9 <PID>
```

### Test script can't connect
```bash
# Make sure server is running first
python -m uvicorn src.main:app --reload

# Check the URL
python api_test.py list-scenarios --url http://localhost:8000
```

### Breakpoints not working
1. Make sure you started with F5 (not command line)
2. Check breakpoint is in the code path being executed
3. Verify `.vscode/launch.json` has `"justMyCode": false`

### Too many logs
```bash
# Use higher log level
LOG_LEVEL=WARNING python -m uvicorn src.main:app --reload
python api_test.py generate "test" --log-level WARNING
```

## 📞 Getting Help

If you need help:
1. Check the relevant guide (API_TESTING_GUIDE.md or DEBUGGING_GUIDE.md)
2. Run with DEBUG logging to see what's happening
3. Set breakpoints and inspect variables
4. Save logs to a file for analysis

---

**Everything is ready to use!** Start the server, run a test, and set some breakpoints to see it all in action. 🚀
