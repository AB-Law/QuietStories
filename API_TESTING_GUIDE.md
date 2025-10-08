# API Testing Guide - HTTP Mode

The `api_test.py` script now makes **real HTTP requests** to your running FastAPI server, allowing you to test your APIs exactly as they'll be used in production.

## Quick Start

### Step 1: Start Your FastAPI Server

You have two options:

**Option A: Debug Mode in VSCode (Recommended)**
1. Press `F5` in Cursor/VSCode
2. Select "FastAPI: Run Server" from the dropdown
3. Set breakpoints in your API code
4. Server starts with debugger attached

**Option B: Command Line**
```bash
python -m uvicorn src.main:app --reload
```

### Step 2: Run Tests

In a **separate terminal**, run the test script:

```bash
# Simple test
python api_test.py list-scenarios

# With logging
python api_test.py generate "A fantasy adventure" --log-level DEBUG
```

## Usage Examples

### Test Single Endpoints

```bash
# Test prompt enrichment
python api_test.py enrich "A detective mystery in 1920s New York"

# Test scenario generation
python api_test.py generate "A space adventure on Mars"

# List scenarios
python api_test.py list-scenarios

# Get specific scenario
python api_test.py get-scenario abc-123-xyz

# Compile scenario
python api_test.py compile abc-123-xyz

# Create session
python api_test.py create-session abc-123-xyz --seed 42

# Process turn
python api_test.py process-turn session-id --action "explore the cave"

# List sessions
python api_test.py list-sessions
```

### Test Full Workflow

```bash
# Test the complete workflow: enrich → generate → compile → session → turn
python api_test.py workflow "A pirate adventure on the high seas"
```

This will:
1. Enrich the prompt
2. Generate the scenario
3. Compile and validate it
4. Create a session
5. Process the first turn

## Debugging Your APIs

### Method 1: Debug While Testing (Recommended)

1. **Start server in debug mode** (Press F5 in Cursor)
2. **Set breakpoints** in your API code (e.g., `src/api/scenarios.py`)
3. **Run test script** in terminal:
   ```bash
   python api_test.py generate "test scenario" --log-level DEBUG
   ```
4. **Execution pauses** at your breakpoints!
5. **Inspect variables**, step through code, use Debug Console

### Method 2: View Server Logs

With the server running, you'll see detailed logs:

```bash
# In Terminal 1: Start server with DEBUG logging
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload

# In Terminal 2: Run test
python api_test.py generate "test scenario"
```

### Method 3: Test Script Logs

The test script also has detailed logging:

```bash
# See detailed request/response info
python api_test.py workflow "test" --log-level DEBUG

# Save logs to file
python api_test.py workflow "test" \
  --log-level DEBUG \
  --log-file logs/test.log
```

## Advanced Options

### Custom Server URL

```bash
# Test against different server
python api_test.py list-scenarios --url http://localhost:8001

# Test against remote server
python api_test.py list-scenarios --url https://api.example.com
```

### Logging Levels

```bash
# Minimal output
python api_test.py generate "test" --log-level ERROR

# Normal operation
python api_test.py generate "test" --log-level INFO

# Detailed debugging
python api_test.py generate "test" --log-level DEBUG

# Save to file
python api_test.py generate "test" \
  --log-level DEBUG \
  --log-file logs/test-$(date +%Y%m%d-%H%M%S).log
```

## Complete Debugging Workflow

Here's a complete example of debugging an API endpoint:

### 1. Identify the Issue

```bash
# Run test and see the error
python api_test.py generate "test scenario" --log-level INFO
```

### 2. Start Server with Debugger

```bash
# In Cursor/VSCode:
# - Open src/api/scenarios.py
# - Set breakpoint at line 59 (ScenarioGenerator creation)
# - Press F5 to start debugging
# - Select "FastAPI: Run Server"
```

### 3. Run Test Again

```bash
# In separate terminal
python api_test.py generate "test scenario" --log-level DEBUG
```

### 4. Debug

When execution pauses at your breakpoint:

- **Check** `request.description` in Variables panel
- **Hover** over variables to see values
- **Step through** code with F10 (step over) or F11 (step into)
- **Evaluate** expressions in Debug Console:
  ```python
  request.description
  generator.provider.__class__.__name__
  len(scenarios_db)
  ```

### 5. Fix and Repeat

- Make your changes
- Server auto-reloads (if using `--reload`)
- Run test again

## Troubleshooting

### "Cannot connect to server"

```bash
✗ Cannot connect to server at http://localhost:8000
```

**Solution**: Start the FastAPI server first:
```bash
python -m uvicorn src.main:app --reload
```

Or press F5 in Cursor/VSCode.

### "HTTP Error 404" or "HTTP Error 500"

The server is running but the endpoint failed. Check:

1. **Server logs** for error details
2. **Test script output** with `--log-level DEBUG`
3. Set **breakpoints** in your API code and debug

### Server Not Auto-Reloading

If you make changes but server doesn't reload:

```bash
# Make sure --reload is specified
python -m uvicorn src.main:app --reload

# Or restart the debug session in VSCode
```

### Can't See Debug Variables

1. Make sure `"justMyCode": false` in `.vscode/launch.json`
2. Check breakpoint is in the actual execution path
3. Try adding `print()` statements before the breakpoint

## Comparison: Old vs New

### Old Way (Direct Function Calls)

```python
# Imported and called functions directly
from src.api.scenarios import generate_scenario
result = await generate_scenario(request)
```

❌ Didn't test HTTP layer  
❌ Didn't test middleware  
❌ Didn't test routing  
❌ Required server code in test process

### New Way (HTTP Requests)

```python
# Makes real HTTP requests
response = await client.post("/scenarios/generate", json=payload)
result = response.json()
```

✅ Tests full HTTP stack  
✅ Tests middleware and routing  
✅ Tests as it will be used  
✅ Server runs separately  
✅ Perfect for debugging with breakpoints

## Tips & Best Practices

### 1. Use Two Terminals

```bash
# Terminal 1: Server with DEBUG logging
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload

# Terminal 2: Run tests
python api_test.py generate "test"
```

### 2. Start with Simple Tests

```bash
# First check server is running
python api_test.py list-scenarios

# Then try simple operations
python api_test.py enrich "short test"

# Then try complex workflows
python api_test.py workflow "full scenario"
```

### 3. Use Appropriate Log Levels

```bash
# Development: Use DEBUG
python api_test.py generate "test" --log-level DEBUG

# Testing: Use INFO
python api_test.py generate "test" --log-level INFO

# CI/CD: Use WARNING
python api_test.py generate "test" --log-level WARNING
```

### 4. Save Logs for Complex Issues

```bash
mkdir -p logs
python api_test.py workflow "complex scenario" \
  --log-level DEBUG \
  --log-file logs/workflow-$(date +%Y%m%d-%H%M%S).log
```

Then review the log file for detailed traces.

### 5. Combine with Breakpoints

1. Set breakpoint in API code
2. Start server in debug mode (F5)
3. Run test script
4. Inspect variables when paused
5. Check test script output for request/response

## Examples for Common Scenarios

### Debugging Scenario Generation

```bash
# Terminal 1: Start in debug mode (or press F5 in VSCode)
# Set breakpoint at src/api/scenarios.py:63

# Terminal 2: Run test
python api_test.py generate "A fantasy adventure" --log-level DEBUG

# When paused at breakpoint:
# - Check request.description
# - Step into generator.generate_scenario()
# - Watch the LLM response
```

### Debugging Turn Processing

```bash
# Terminal 1: Set breakpoint at src/api/sessions.py:180

# Terminal 2: First create a session
SCENARIO_ID=$(python api_test.py generate "test" --log-level ERROR | grep "ID:" | cut -d' ' -f2)
python api_test.py compile $SCENARIO_ID
SESSION_ID=$(python api_test.py create-session $SCENARIO_ID --log-level ERROR | grep "Session ID:" | cut -d' ' -f3)

# Then process turn (will hit breakpoint)
python api_test.py process-turn $SESSION_ID --action "explore" --log-level DEBUG
```

### Testing Error Handling

```bash
# Try invalid scenario ID
python api_test.py compile "invalid-id" --log-level DEBUG

# Try invalid session ID  
python api_test.py process-turn "invalid-session" --log-level DEBUG
```

## Next Steps

1. ✅ Start server in debug mode
2. ✅ Set breakpoints in your API code
3. ✅ Run `api_test.py` commands
4. ✅ Debug when execution pauses
5. ✅ Fix issues and repeat

For more debugging techniques, see:
- `DEBUGGING_GUIDE.md` - Complete debugging reference
- `debug_examples.py` - Examples of debug utilities

Happy debugging! 🐛🔍
