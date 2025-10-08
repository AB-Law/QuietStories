# QuietStories Enhancement Plan

## Overview

Fix multiple UX and functionality issues: remove off-putting endings, add response streaming, enable agentic LLM behavior with tools, fix input textarea, persist character bios, and resolve memory display bugs.

## Issues Identified

### 1. Off-putting narrative endings

**Root Cause**: LLM naturally adds dramatic "What will you do next?" style endings.
**Location**: `src/prompts.py` NARRATOR_SYSTEM prompt (lines 106-208)
**Fix**: Add explicit instruction to avoid meta-prompting and dramatic closings.

### 2. Input box not resizing / no newlines

**Root Cause**: Using `Input` component (single-line) instead of textarea.
**Location**: `frontend/src/components/Chat.tsx` (lines 455-462)
**Fix**: Replace Input with auto-resizing textarea component.

### 3. No streaming - text pops up and scrolls

**Root Cause**: Response is sent as single chunk, auto-scroll runs immediately.
**Locations**:

- Backend: `src/api/sessions.py` process_turn endpoint (lines 222-373)
- Frontend: `frontend/src/components/Chat.tsx` sendMessage function (lines 194-248)
**Fix**: Implement Server-Sent Events (SSE) streaming with word/chunk-based output.

### 4. Agentic approach not working

**Root Cause**: Tools compiled but never passed to LLM. Currently using `json_schema` for structured output which bypasses tool calling.
**Locations**:

- `src/engine/orchestrator.py` process_turn (lines 83-153)
- `src/engine/compiler.py` (tools created but unused)
**Fix**: Enable multi-turn agentic flow where LLM can:
- Call tools to query/update state
- Create characters dynamically
- Think step-by-step before generating narrative
- Use state_changes more actively

### 5. Character bios disappear after first chat

**Root Cause**: Entities might not include backgrounds after state changes, or sidebar reference is stale.
**Location**: `frontend/src/components/Chat.tsx` sidebar entities display (lines 506-532)
**Fix**: Ensure entity backgrounds persist through updates and are properly returned in session data.

### 6. Admin memories showing "No memories available"

**Root Cause**: LLM not generating `hidden_memory_updates` in responses, so no memories are created.
**Locations**:

- `src/prompts.py` NARRATOR_SYSTEM (needs examples/encouragement)
- `src/engine/orchestrator.py` _update_memory (lines 555-586)
- Memory only created when LLM explicitly includes hidden_memory_updates
**Fix**: Improve prompt to encourage memory creation with concrete examples.

## Implementation Plan

### Task 1: Fix narrative endings

**Files**: `src/prompts.py`

- Add instruction in NARRATOR_SYSTEM around line 206:
- "End narratives naturally with the scene, not with meta-prompts"
- "Avoid phrases like 'What will you do next?' or 'The choice is yours'"
- "You may hint at possibilities within the narrative, but don't directly prompt the player"

### Task 2: Replace input with auto-resize textarea

**Files**: `frontend/src/components/Chat.tsx`

- Replace Input component (line 455) with textarea
- Add auto-resize logic based on content
- Update handleKeyPress to only submit on Enter without Shift (line 250-259)
- Style to match existing Input appearance

### Task 3: Implement streaming responses

**Backend** (`src/api/sessions.py`):

- Modify process_turn endpoint to support streaming
- Stream LLM response word-by-word or in small chunks
- Use FastAPI StreamingResponse with SSE format

**Frontend** (`frontend/src/components/Chat.tsx`, `frontend/src/services/api.ts`):

- Add streaming mode to processTurn API call
- Use EventSource or fetch with streaming
- Accumulate chunks and update message in real-time
- Disable auto-scroll or scroll intelligently (keep reading position)

### Task 4: Enable agentic tool-calling flow

**Files**: `src/engine/orchestrator.py`, `src/engine/compiler.py`, `src/prompts.py`

**Approach**:

1. Create utility tools for state management:

- `read_state(path)` - query current state
- `update_state(op, path, value)` - modify state
- `create_character(entity_data)` - add new character
- `update_world(changes)` - modify world state
- `add_memory(entity_id, content, visibility)` - record memory

2. Modify orchestrator to support multi-turn tool calling:

- Pass tools to LLM instead of json_schema initially
- Let LLM call tools (query state, plan changes)
- After tool calls complete, ask for final narrative with json_schema
- Maximum 3-5 tool call rounds to prevent loops

3. Update NARRATOR_SYSTEM prompt:

- Explain available tools
- Encourage using tools to check state before narrating
- Encourage creating characters when introducing NPCs
- Encourage updating world state (time, weather, etc.)

**Note**: This is the most complex change, requiring agentic loop implementation.

### Task 5: Fix character bio persistence

**Files**: `src/api/sessions.py`, `src/engine/orchestrator.py`

- Ensure entities list with backgrounds is properly saved after each turn (line 313-327)
- Verify entity data includes background field in all updates
- Check that get_session returns full entity data including backgrounds

### Task 6: Fix memory display bug

**Files**: `src/prompts.py`, `src/engine/orchestrator.py`

- Add memory creation examples to NARRATOR_SYSTEM (around lines 159-206)
- Show format: `"hidden_memory_updates": [{"target_id": "npc_id", "content": "thought", "scope": "private", "visibility": "private"}]`
- Add reminder: "Record NPC thoughts and important observations using hidden_memory_updates"
- Verify memory creation in orchestrator _update_memory function
- Add debug logging to track when memories are created

## Implementation Order

1. Task 1 (endings) - Quick prompt fix
2. Task 6 (memories) - Prompt improvements with examples  
3. Task 2 (textarea) - Frontend UI fix
4. Task 5 (character persistence) - Backend data fix
5. Task 3 (streaming) - Backend + Frontend streaming
6. Task 4 (agentic) - Complex multi-turn tool calling

## Files to Modify

- `src/prompts.py` - Narrator prompts (Tasks 1, 6, 4)
- `frontend/src/components/Chat.tsx` - UI and streaming (Tasks 2, 3)
- `frontend/src/services/api.ts` - API streaming support (Task 3)
- `src/api/sessions.py` - Streaming endpoint (Task 3, Task 5)
- `src/engine/orchestrator.py` - Agentic flow (Task 4, Task 5)
- `src/engine/compiler.py` - Utility tools (Task 4)