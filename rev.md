# Enhanced LLM Memory & Tool-Calling System

## Current Issues Identified

1. **Unclear tool usage patterns**: LLM doesn't consistently call memory/state tools
2. **Passive memory system**: Memories are provided in context but LLM doesn't actively query or update them
3. **No autonomous triggering**: System relies on LLM remembering to use tools rather than prompting/guiding it
4. **Limited memory structure**: Only private/public distinction, no scoped memory types (relationships, beliefs, events)
5. **No reflection phase**: Memory updates happen inline with narrative generation, easy to forget

## Proposed Architecture

### 1. Hybrid Memory Retrieval

**Files**: `backend/engine/orchestrator.py`, `backend/engine/memory.py`

- **Automatic baseline**: Always provide recent memories (last 5-10 turns) in initial context
- **On-demand querying**: Add tools for LLM to query specific memory types
- **Keep existing**: `add_memory` tool for recording new memories

### 2. Improved Tool Prompting & Guidance

**Files**: `backend/prompts.py`, `backend/engine/compiler.py`

- Add explicit guidance in `NARRATOR_SYSTEM` about when to call tools
- Add examples of good tool usage patterns in prompt
- Emphasize that ignoring tools for multiple turns leads to inconsistent story

### 3. Scoped Memory Types ✅ COMPLETED

**Files**: `backend/engine/memory.py`, `backend/schemas/outcome.py`

Expand memory structure: beliefs, relationships, events, locations, goals

### 4. Semantic Memory Search (Phase 2)

**New files**: `backend/engine/memory_search.py`

Use vector DB (ChromaDB/FAISS) for semantic memory retrieval

### 5. Reflection Phase After Narrative

**Files**: `backend/engine/orchestrator.py`

Add dedicated reflection step in Langgraph workflow after outcome generation

### 6. Tool Call Monitoring & Feedback

**Files**: `backend/engine/orchestrator.py`

Track tool usage frequency, inject reminders when tools underused for 3+ turns

---

## Additional UX Improvements

### 7. Streaming Narrative Generation ✅ COMPLETED

**Files**: `backend/api/sessions.py`, `backend/providers/base.py`, `frontend/src/components/Chat.tsx`

Enable SSE streaming for turn processing, stream narrative token-by-token

### 8. Suggested Actions / Quick Replies ✅ COMPLETED

**Files**: `backend/engine/orchestrator.py`, `backend/schemas/outcome.py`, `frontend/src/components/Chat.tsx`

Add `suggested_actions` to Outcome, LLM generates 3-5 contextual suggestions

### 9. Rich Narrative Formatting

**Files**: `backend/schemas/outcome.py`, `frontend/src/components/Chat.tsx`

Add markdown support, dialogue formatting, better typography

### 10. Character Relationship Visualization

**Files**: New `frontend/src/components/RelationshipGraph.tsx`, `backend/api/sessions.py`

Network graph showing character relationships with trust/affection levels

### 11. Turn Undo/Branching

**Files**: `backend/api/sessions.py`, `backend/db/manager.py`, `frontend/src/components/Chat.tsx`

Store state snapshots, allow rewind to previous turns, explore branches

### 12. Save/Load Checkpoints

**Files**: `backend/api/sessions.py`, `frontend/src/components/Chat.tsx`

Save checkpoints with descriptions, restore to any checkpoint, export/import

### 13. Narrative Quality Feedback

**Files**: New `backend/api/feedback.py`, `frontend/src/components/Chat.tsx`

Add 👍/👎 buttons, store feedback, regenerate option

### 14. Mobile-Optimized Experience

**Files**: `frontend/src/components/Chat.tsx`, `frontend/src/index.css`

Responsive design, collapsible sidebar, touch targets, swipe gestures

### 15. Performance Optimizations

**Files**: `backend/engine/orchestrator.py`, `backend/providers/base.py`

Cache responses, parallel tool execution, smart summarization, Redis caching

---

## Decision-Making & Storytelling Improvements

### 16. Intelligent Roll Resolution System ✅ COMPLETED

**Files**: `backend/engine/orchestrator.py`, `backend/schemas/outcome.py`

Add roll resolution: d20 + character stats vs difficulty, feed results back to LLM

### 17. Dynamic Difficulty Adjustment

**Files**: `backend/engine/orchestrator.py`, `backend/engine/validator.py`

Track success rate, adjust difficulty using negativity_budget decay rates

### 18. Consequence Propagation System

**Files**: `backend/engine/orchestrator.py`, `backend/schemas/outcome.py`

Add delayed_effects to Outcome, store pending consequences, trigger after N turns

### 19. Contextual Action Filtering ✅ COMPLETED

**Files**: `backend/engine/orchestrator.py`, `backend/utils/jsonlogic.py`

Implement precondition checking (currently TODO), filter by location/resources/state

### 20. Emotional State Tracking

**Files**: `backend/engine/memory.py`, `backend/schemas/outcome.py`

Add emotional states to entities, track in scoped memories, emotions decay over time

### 21. Narrative Pacing Control

**Files**: `backend/prompts.py`, `backend/engine/orchestrator.py`

Track story beats, add pacing hints to LLM, detect stagnation, inject pacing events

### 22. Multi-Path Story Branching

**Files**: `backend/engine/orchestrator.py`, `backend/schemas/scenario.py`

Define story branches in spec, track current branch, trigger branch points

### 23. Environmental Storytelling

**Files**: `backend/engine/orchestrator.py`, `backend/prompts.py`

Track world state (weather/time/seasons), environmental effects influence gameplay

### 24. Foreshadowing & Setup/Payoff

**Files**: `backend/engine/orchestrator.py`, `backend/engine/memory.py`

LLM plants story seeds, track foreshadowed elements, remind LLM of setups

### 25. Character Arc Tracking

**Files**: `backend/engine/memory.py`, `backend/schemas/outcome.py`

Define arc stages, track development in scoped memories, trigger milestones

---

## Priority Recommendations

**Immediate Impact (Do First)** ✅ **ALL COMPLETED**:

1. ✅ Streaming narrative (biggest perceived performance boost)
2. ✅ Suggested actions (reduces friction, improves engagement)
3. ✅ Memory system improvements (core functionality)
4. ✅ Roll resolution system (adds actual gameplay)
5. ✅ Contextual action filtering (fixes TODO, improves realism)

**High Value (Do Soon)**:

6. Rich formatting (better reading experience)
9. Turn undo (safety net, experimentation)
10. Save checkpoints (user confidence)
7. Consequence propagation (actions feel meaningful)
8. Emotional state tracking (believable NPCs)

**Nice to Have (Later)**:

11. Dynamic difficulty (better pacing)
12. Narrative pacing control (story structure)
13. Foreshadowing system (professional storytelling)
14. Character arc tracking (deeper characters)
15. Multi-path branching (replayability)
16. Environmental storytelling (immersion)
17. Relationship visualization (cool feature)
18. Mobile optimization (expand audience)
19. Feedback system (continuous improvement)
20. Performance optimizations (scale)
21. Advanced memory consolidation (optimize context)
22. Smart context building (improve LLM prompts)

---

## 📋 Implementation To-Do List

### **High Value (Do Soon)** - Click to Complete ✅

- [ ] **6. Rich formatting** - Add markdown support, dialogue formatting, better typography
- [ ] **9. Turn undo** - Store state snapshots, allow rewind to previous turns
- [ ] **10. Save checkpoints** - Save checkpoints with descriptions, restore functionality
- [ ] **7. Consequence propagation** - Add delayed effects to Outcome schema
- [x] **8. Emotional state tracking** - Add emotional states to entities, track in scoped memories

### **Nice to Have (Later)** - Click to Complete 📋

- [ ] **13. Foreshadowing system** - LLM plants story seeds, tracks foreshadowed elements
- [ ] **14. Character arc tracking** - Define arc stages, track development in scoped memories
- [ ] **12. Narrative pacing control** - Track story beats, add pacing hints to LLM
- [ ] **11. Dynamic difficulty** - Track success rate, adjust difficulty dynamically
- [ ] **15. Multi-path branching** - Define story branches in spec, track current branch
- [ ] **16. Environmental storytelling** - Track world state (weather/time/seasons)
- [x] **17. Relationship visualization** - Network graph showing character relationships
- [ ] **18. Mobile optimization** - Responsive design, collapsible sidebar, touch targets
- [ ] **19. Feedback system** - Add 👍/👎 buttons, store feedback, regenerate option
- [x] **20. Performance optimizations** - Cache responses, parallel tool execution, Redis caching
- [x] **21. Advanced memory consolidation** - System to summarize and consolidate memories over time

---

## 🎯 **Next Recommended Steps**

1. **Start with Rich Formatting** - Immediate visual improvement to narratives
2. **Implement Turn Undo** - Builds user confidence for experimentation
3. **Add Save Checkpoints** - Complements turn undo for safety net
4. **Work on Consequence Propagation** - Deepens gameplay meaningfulness
5. **Implement Dynamic Difficulty** - Track success rate, adjust difficulty dynamically

**Total Progress: 9/21 features completed (43%)** 🚀

---

## 📝 **Rich Formatting Implementation Notes**

**Status**: Partially implemented (ReactMarkdown installed, basic structure in place)

**Remaining Work**:
- Configure Tailwind Typography plugin properly
- Add dialogue formatting (character names, quotes)
- Style different text elements (bold, italic, headers)
- Ensure responsive typography across devices
- Add syntax highlighting for any code blocks if needed

**Files Modified**:
- `frontend/package.json` - Added react-markdown dependency
- `frontend/src/components/Chat.tsx` - Added ReactMarkdown import and conditional rendering
- `frontend/tailwind.config.js` - Added typography plugin (needs testing)

**Next Steps**:
1. Test markdown rendering in development
2. Add custom components for dialogue formatting
3. Style prose elements with proper spacing and typography
4. Ensure accessibility and mobile responsiveness