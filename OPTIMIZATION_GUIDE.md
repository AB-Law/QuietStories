# QuietStories - LLM Optimization & LMStudio Guide

This guide covers the new LLM optimization features and LMStudio local model support added to QuietStories.

## Table of Contents
- [LMStudio Setup](#lmstudio-setup)
- [Optimization Features](#optimization-features)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Performance Tips](#performance-tips)

---

## LMStudio Setup

### What is LMStudio?

LMStudio is a desktop application that lets you run large language models locally on your computer. It provides an OpenAI-compatible API, making it easy to integrate with QuietStories.

### Installation & Setup

1. **Download LMStudio**
   - Visit: https://lmstudio.ai/
   - Download and install for your OS

2. **Load a Model**
   - Open LMStudio
   - Browse models (recommended: Mistral 7B, Llama 2 7B, or similar)
   - Download and load your chosen model
   - Start the local server (usually on port 5101)

3. **Configure QuietStories**

Edit your `.env` file:

```bash
# Set provider to lmstudio
MODEL_PROVIDER=lmstudio

# LMStudio default endpoint (update port if different)
OPENAI_API_BASE=http://localhost:5101/v1

# Model name (can be anything for LMStudio)
MODEL_NAME=local-model

# API key not required for LMStudio
OPENAI_API_KEY=not-required
```

4. **Start QuietStories**

```bash
python -m uvicorn backend.main:app --reload
```

5. **Verify Connection**

Visit: http://localhost:8000/docs

Try the `/optimization/stats` endpoint to verify the system is working.

---

## Optimization Features

QuietStories now includes comprehensive optimization to reduce token usage and improve performance, especially important for local LLMs with limited context windows.

### Key Features

1. **Context Caching**
   - Caches frequently used context strings
   - Reduces repeated token usage
   - LRU-style eviction when cache grows

2. **Message Optimization**
   - Smart sliding window for conversation history
   - Removes redundant messages
   - Keeps system prompts intact
   - Targets configurable token limits

3. **Memory Summarization**
   - Filters memories by importance
   - Keeps only recent/relevant memories
   - Compresses long memory content
   - Configurable per-entity limits

4. **Automatic Memory Consolidation**
   - Runs every 10 turns automatically
   - Removes low-importance memories
   - Keeps memory size manageable
   - Prevents context bloat over long sessions

### How It Works

```
User Input → Build Context → Optimize Messages → Call LLM → Process Response
                ↑                    ↑
         Memory Manager      Reduce Tokens
                                (4000 default)
```

The optimizer:
1. Estimates token usage
2. If over limit, applies sliding window
3. Prioritizes recent messages
4. Preserves critical system context

---

## Configuration

### Optimization Presets

QuietStories provides 4 presets optimized for different scenarios:

#### 1. Local LLM (Recommended for LMStudio)
```bash
curl -X POST http://localhost:8000/optimization/presets/local_llm
```

**Settings:**
- Max turn history: 5
- Max memories per entity: 5
- Max context tokens: 2000
- Caching: Enabled

**Best for:** Local models with 4K-8K context windows

#### 2. Cloud LLM
```bash
curl -X POST http://localhost:8000/optimization/presets/cloud_llm
```

**Settings:**
- Max turn history: 15
- Max memories per entity: 15
- Max context tokens: 8000
- Caching: Enabled

**Best for:** GPT-4, Claude, or other cloud models

#### 3. Minimal
```bash
curl -X POST http://localhost:8000/optimization/presets/minimal
```

**Settings:**
- Max turn history: 3
- Max memories per entity: 3
- Max context tokens: 1000
- Caching: Enabled

**Best for:** Very small models or fastest performance

#### 4. Maximum
```bash
curl -X POST http://localhost:8000/optimization/presets/maximum
```

**Settings:**
- Max turn history: 30
- Max memories per entity: 30
- Max context tokens: 16000
- Caching: Disabled

**Best for:** Best quality with large context models

### Custom Configuration

You can fine-tune optimization settings via API:

```bash
curl -X POST http://localhost:8000/optimization/config \
  -H "Content-Type: application/json" \
  -d '{
    "max_turn_history": 7,
    "max_memories_per_entity": 8,
    "max_context_tokens": 3000,
    "enable_caching": true
  }'
```

### View Current Config

```bash
curl http://localhost:8000/optimization/config
```

---

## API Endpoints

### GET `/optimization/config`
Get current optimization configuration.

**Response:**
```json
{
  "max_turn_history": 10,
  "max_memories_per_entity": 10,
  "max_context_tokens": 4000,
  "enable_caching": true
}
```

### POST `/optimization/config`
Update optimization configuration.

**Request Body:**
```json
{
  "max_turn_history": 5,
  "max_memories_per_entity": 5,
  "max_context_tokens": 2000,
  "enable_caching": true
}
```

### GET `/optimization/stats`
Get optimization statistics.

**Response:**
```json
{
  "cache_stats": {
    "size": 15,
    "max_size": 50,
    "total_accesses": 142
  },
  "current_config": {
    "max_turn_history": 10,
    "max_memories_per_entity": 10,
    "max_context_tokens": 4000,
    "enable_caching": true
  }
}
```

### POST `/optimization/cache/clear`
Clear all optimization caches.

**Response:**
```json
{
  "status": "success",
  "message": "Optimization caches cleared"
}
```

### GET `/optimization/presets`
List available optimization presets.

### POST `/optimization/presets/{preset_name}`
Apply a preset configuration.

**Example:**
```bash
curl -X POST http://localhost:8000/optimization/presets/local_llm
```

---

## Performance Tips

### For Local LLMs (LMStudio)

1. **Use the local_llm preset**
   ```bash
   curl -X POST http://localhost:8000/optimization/presets/local_llm
   ```

2. **Choose appropriate models**
   - **Best:** Mistral 7B Instruct, Llama 2 7B Chat
   - **Avoid:** Models larger than 13B (slow on most hardware)
   - **Context window:** Prefer models with 4K+ context

3. **Optimize LMStudio settings**
   - GPU acceleration: ON
   - Context length: 4096 (matches optimization default)
   - Temperature: 0.7 (good balance)
   - Max tokens: 2048

4. **Monitor token usage**
   - Check logs for "Optimized messages" counts
   - If still slow, reduce `max_context_tokens` further
   - Use `GET /optimization/stats` to monitor cache hits

### For Cloud LLMs (OpenAI, etc.)

1. **Use the cloud_llm preset**
   ```bash
   curl -X POST http://localhost:8000/optimization/presets/cloud_llm
   ```

2. **For very long sessions (50+ turns)**
   - Memory consolidation runs automatically
   - Check memory stats: `GET /sessions/{id}/memories`
   - Manually consolidate if needed

3. **Cost optimization**
   - Enable caching to reduce API calls
   - Use `minimal` preset for development/testing
   - Switch to `cloud_llm` for production

### General Tips

1. **Session Management**
   - Export important sessions: `GET /sessions/{id}/export` (coming soon)
   - Clear old sessions periodically
   - Memory consolidates automatically every 10 turns

2. **Debugging Performance**
   ```python
   # Check token estimates in logs
   LOG_LEVEL=DEBUG python -m uvicorn backend.main:app --reload
   
   # Look for lines like:
   # [Optimizer] Current estimated tokens: 3500
   # [Optimizer] Reduced from 20 to 15 messages (3500 -> 2200 tokens)
   ```

3. **Cache Management**
   - Cache clears automatically (LRU eviction)
   - Manually clear if behavior seems stale:
     ```bash
     curl -X POST http://localhost:8000/optimization/cache/clear
     ```

---

## Troubleshooting

### LMStudio Connection Issues

**Problem:** "LMStudio API error: Connection refused"

**Solutions:**
1. Verify LMStudio server is running (check LMStudio UI)
2. Check port number in `.env` matches LMStudio
3. Try: `curl http://localhost:5101/v1/models`
4. Restart LMStudio server

### Slow Generation

**Problem:** Story generation takes too long

**Solutions:**
1. Apply minimal preset:
   ```bash
   curl -X POST http://localhost:8000/optimization/presets/minimal
   ```
2. Use smaller model (7B instead of 13B)
3. Enable GPU acceleration in LMStudio
4. Reduce `max_context_tokens` further:
   ```bash
   curl -X POST http://localhost:8000/optimization/config \
     -H "Content-Type: application/json" \
     -d '{"max_context_tokens": 1500}'
   ```

### Memory Issues

**Problem:** "Out of memory" or very slow after many turns

**Solutions:**
1. Memory consolidation should run automatically every 10 turns
2. Check if it's working: Look for log message "Triggering memory consolidation"
3. Restart session if issue persists
4. Reduce memory limits:
   ```bash
   curl -X POST http://localhost:8000/optimization/config \
     -H "Content-Type: application/json" \
     -d '{"max_memories_per_entity": 3}'
   ```

### Quality Issues

**Problem:** LLM seems to forget important details

**Solutions:**
1. Increase context limits:
   ```bash
   curl -X POST http://localhost:8000/optimization/presets/cloud_llm
   ```
2. Check memory is being saved: `GET /sessions/{id}/memories`
3. Verify model has sufficient context window (4K minimum)
4. Disable aggressive optimization:
   ```bash
   curl -X POST http://localhost:8000/optimization/config \
     -H "Content-Type: application/json" \
     -d '{"max_turn_history": 15, "max_memories_per_entity": 15}'
   ```

---

## Monitoring & Metrics

### Check Optimization Performance

```bash
# Get statistics
curl http://localhost:8000/optimization/stats

# Response shows:
# - Cache hit/miss rates
# - Current configuration
# - Total cache accesses

# Example response:
{
  "cache_stats": {
    "size": 25,        # Current cache size
    "max_size": 50,    # Cache capacity
    "total_accesses": 342  # Total lookups
  },
  "current_config": { ... }
}
```

### Check Memory Statistics

```bash
# Get session memory stats
curl http://localhost:8000/sessions/{session_id}

# Look for:
# - turn: Current turn number
# - entities: Entity count
# - private_memory/public_memory: Memory sizes
```

### Log Monitoring

Enable debug logging to see optimization in action:

```bash
LOG_LEVEL=DEBUG python -m uvicorn backend.main:app --reload
```

Look for these log messages:
- `[Optimizer] Current estimated tokens: XXXX`
- `[Optimizer] Reduced from X to Y messages`
- `[Orchestrator] Triggering memory consolidation`
- `[Cache] Hit for key: ...` (cache working)
- `[LMStudio] Sending request to http://localhost:5101/v1`

---

## Example: Complete LMStudio Workflow

```bash
# 1. Configure for LMStudio
export MODEL_PROVIDER=lmstudio
export OPENAI_API_BASE=http://localhost:5101/v1
export MODEL_NAME=mistral-7b

# 2. Start backend
python -m uvicorn backend.main:app --reload

# 3. Apply optimization preset
curl -X POST http://localhost:8000/optimization/presets/local_llm

# 4. Create a session
curl -X POST http://localhost:8000/scenarios/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "A detective mystery in a small town"}'

# (Save scenario ID from response)

curl -X POST http://localhost:8000/scenarios/{scenario_id}/compile

curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "{scenario_id}", "seed": 42}'

# (Save session ID from response)

# 5. Play the game
curl -X POST http://localhost:8000/sessions/{session_id}/turns \
  -H "Content-Type: application/json" \
  -d '{"action": "Investigate the crime scene"}'

# 6. Monitor optimization
curl http://localhost:8000/optimization/stats

# 7. Adjust if needed
curl -X POST http://localhost:8000/optimization/config \
  -H "Content-Type: application/json" \
  -d '{"max_context_tokens": 1500}'
```

---

## Summary

QuietStories now provides:

✅ **LMStudio Support** - Run stories with local models  
✅ **Smart Optimization** - Automatic token reduction  
✅ **Memory Consolidation** - Prevents context bloat  
✅ **Flexible Configuration** - Presets + custom settings  
✅ **Performance Monitoring** - Track optimization metrics  

**Recommended setup for most users:**

```bash
MODEL_PROVIDER=lmstudio
```

```bash
curl -X POST http://localhost:8000/optimization/presets/local_llm
```

Enjoy faster, more efficient story generation! 🚀

