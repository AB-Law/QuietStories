# Performance & Memory Optimization Plan

## Overview

Optimize the QuietStories narrative engine to reduce response latency and API costs while maintaining high-quality story generation. Key improvements include session-isolated vector databases, relationship graph tracking, hybrid streaming architecture, and intelligent tool batching.

## Current Issues

1. **Vector DB Cross-Contamination**: All sessions share one ChromaDB collection, causing memory leaks between unrelated stories
2. **High Tool Call Volume**: 7-11 tool calls per turn, hitting the 10-call limit
3. **No Relationship Tracking**: Relationships stored as text memories only, no structured graph
4. **Slow Response Time**: Tools → full generation → chunked streaming (not true streaming)
5. **High Token Usage**: ~6,500-9,500 input tokens per turn (verbose prompts + context)

## Implementation Strategy

### Phase 1: Session-Scoped Vector Database (Critical Fix)

**Problem**: ChromaDB uses single collection "entity_memories" for all sessions

**Solution**:

- Modify `SemanticMemorySearch.__init__()` to accept `session_id` parameter
- Use collection naming: `f"session_{session_id}"` for complete isolation
- Update `MemoryManager` to pass `session_id` to semantic search
- Add collection cleanup on session deletion

**Files to modify**:

- `backend/engine/memory_search.py` (lines 38-103)
- `backend/engine/memory.py` (line 59)
- `backend/api/sessions.py` (add cleanup endpoint)

### Phase 2: Relationship Graph System

**Goal**: Bidirectional relationship tracking with LLM integration

**Components**:

1. **In-Memory Graph Structure** (`backend/engine/relationship_graph.py` - NEW):
   ```python
   class RelationshipGraph:
       - nodes: entities
       - edges: (from, to, type, sentiment, strength, last_updated)
       - Methods: add_relationship(), query_relationships(), get_graph_summary()
   ```

2. **Auto-Extraction from Memory Tools**:

            - When `add_memory(scope="relationship")` is called, extract:
                    - Entity mentions (pattern matching)
                    - Relationship type (trust, fear, love, rivalry, etc.)
                    - Sentiment score (keyword analysis)
            - Update graph immediately (no extra LLM calls)

3. **Graph Query Tool** (extend existing tools):

            - Enhance `search_memories` to include relationship queries
            - New parameter: `include_relationships=True`
            - Returns: memories + related relationship edges

4. **Update Tool Descriptions**:

            - `add_memory`: "When scope='relationship', mention both entities. System auto-extracts: trust/fear/love/alliance/rivalry"
            - `search_memories`: "Use include_relationships=True to get relationship context"

**Files to create/modify**:

- `backend/engine/relationship_graph.py` (NEW)
- `backend/engine/memory.py` (integrate graph)
- `backend/engine/compiler.py` (update tool descriptions)
- `backend/api/sessions.py` (add relationship query endpoint)

### Phase 3: Hybrid Streaming Architecture

**Goal**: Stream narrative tokens while tools run, then confirm to LLM

**Flow**:

1. User input arrives
2. Execute "read" tools first (read_state, search_memories, query_relationships)
3. Stream narrative generation with tool context
4. Execute "write" tools after streaming (add_memory, update_state, update_world)
5. Send brief confirmation to LLM with tool results
6. Return complete response to frontend

**Implementation**:

- Modify `TurnOrchestrator.process_turn()` to split tool execution phases
- Implement true token streaming in providers (LangChain `astream()`)
- Update `/sessions/{id}/turns/stream` endpoint
- Add tool confirmation round (short LLM call: "Tools executed: [results]. Acknowledge.")

**Files to modify**:

- `backend/engine/orchestrator.py` (split tool phases, streaming)
- `backend/providers/openai.py` (implement `astream` properly)
- `backend/providers/generic.py` (implement `astream` properly)
- `backend/api/sessions.py` (update streaming endpoint)
- `frontend/src/services/api.ts` (handle streaming)
- `frontend/src/components/Chat.tsx` (consume streaming)

### Phase 4: Tool Batching & Smart Caching

**Goal**: Reduce tool calls from 7-11 to 4-6 per turn

**Optimizations**:

1. **Batch Memory Tool**:
   ```python
   add_memories([
     {entity_id: "elena", content: "...", scope: "relationship"},
     {entity_id: "marcus", content: "...", scope: "belief"}
   ])
   ```


            - Single tool call instead of 3-5 separate calls
            - Auto-extract relationships from batch

2. **Stateful Context Cache**:

            - Cache last 2 turns of state reads
            - Tool: `read_state(path, use_cache=True)`
            - Invalidate on state changes
            - Save 2-3 read_state calls per turn

3. **Combined World Update**:

            - Already supports kwargs: `update_world(time="evening", weather="rainy", location="forest")`
            - Update prompt to encourage batching

**Files to modify**:

- `backend/engine/compiler.py` (new batch tools)
- `backend/engine/orchestrator.py` (state cache)
- `backend/prompts.py` (update tool usage guidelines)

### Phase 5: Prompt Compression

**Goal**: Reduce input tokens from ~3,000 to ~2,000 (33% reduction)

**Changes**:

1. **Consolidate Examples**: Keep 2 best examples, remove redundant ones (~400 tokens saved)
2. **Merge Duplicate Guidelines**: Relationship tracking mentioned 3x, consolidate to 1 section (~300 tokens saved)
3. **Simplify Tool Descriptions**: Remove verbose examples, keep concise usage (~200 tokens saved)
4. **Smart Context Selection**: Only include relevant memory scopes (~100 tokens saved)

**Validation**: Test with existing scenarios to ensure no quality degradation

**Files to modify**:

- `backend/prompts.py` (NARRATOR_SYSTEM, NARRATOR_USER)
- `backend/engine/compiler.py` (tool descriptions)

### Phase 6: Background Relationship Enrichment (Optional Enhancement)

**Goal**: Queue LLM analysis for ambiguous relationships

**Implementation**:

- After turn completion, check for unclear relationships
- Queue async task: analyze relationship sentiment/type with LLM
- Update graph when complete (doesn't block narrative)
- Use FastAPI BackgroundTasks

**Files to modify**:

- `backend/api/sessions.py` (background tasks)
- `backend/engine/relationship_graph.py` (enrichment methods)

## Key Technical Details

### Vector DB Session Isolation

```python
# memory_search.py
def __init__(self, session_id: str, persist_directory: str = "data/chroma_memories"):
    collection_name = f"session_{session_id}"
    self.vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=self.embedding_model,
        persist_directory=persist_directory,
    )
```

### Relationship Graph Auto-Extraction

```python
# When add_memory called with scope="relationship"
if scope == "relationship":
    extracted = extract_relationship(content, entity_id, all_entities)
    # extracted = {from: "elena", to: "marcus", type: "trust", sentiment: 0.7}
    graph.add_relationship(**extracted)
```

### Hybrid Streaming Flow

```python
async def process_turn_streaming(user_input):
    # Phase 1: Read tools
    read_results = await execute_tools(["read_state", "search_memories"])

    # Phase 2: Stream narrative
    async for token in stream_narrative(context + read_results):
        yield token

    # Phase 3: Write tools
    write_results = await execute_tools(["add_memory", "update_state"])

    # Phase 4: Confirm to LLM
    confirmation = await llm.chat([ToolMessage(content=write_results)])
    return confirmation
```

## Testing & Validation

### Test Cases

1. **Session Isolation**: Create 2 sessions, verify memories don't leak
2. **Relationship Extraction**: Test auto-extraction accuracy
3. **Streaming Performance**: Measure time-to-first-token
4. **Tool Batching**: Verify 4-6 calls per turn (down from 7-11)
5. **Prompt Quality**: Compare narrative quality before/after compression

### Metrics to Track

- Average tool calls per turn (target: 4-6, down from 7-11)
- Time to first narrative token (target: <3s, down from ~8s)
- Input tokens per turn (target: ~5,000, down from ~7,500)
- Relationship extraction accuracy (target: >85%)
- Session memory isolation (target: 100%, currently ~0%)

## Documentation Requirements

- Use **Context7 MCP** in Cursor/VSCode for all documentation
- Document relationship graph API
- Update API documentation for streaming endpoints
- Add architecture diagrams for tool flow
- Create relationship extraction pattern guide

## Migration & Rollout

1. Deploy Phase 1 (session isolation) first - critical bug fix
2. Run migration script for existing sessions (create separate collections)
3. Deploy Phases 2-4 together (relationship graph + streaming + batching)
4. Deploy Phase 5 (prompt compression) with A/B testing
5. Phase 6 (background enrichment) as optional enhancement

## Success Criteria

- ✅ No cross-session memory contamination (100% isolation)
- ✅ 30-50% reduction in response latency
- ✅ 20-30% reduction in API costs
- ✅ Structured relationship tracking accessible to LLM
- ✅ No degradation in narrative quality
- ✅ Relationship extraction accuracy >85%
