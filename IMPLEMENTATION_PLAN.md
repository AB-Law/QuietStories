# Dynamic CYOA Engine - Implementation Plan

## Project Overview

This is a Python-based engine that generates dynamic Choose Your Own Adventure (CYOA) scenarios from free-text descriptions, with no hardcoded scenario nouns, supporting both local and remote LLMs through a unified interface.

## Key Architectural Principles

1. **Dynamic Only**: No hand-written rulepacks or scenario nouns in code
2. **Generic Engine**: Works with any scenario description
3. **LLM Agnostic**: Supports OpenAI, Ollama, and generic endpoints
4. **Privacy-First**: Prevents "thought leaks" between entities
5. **Validation-Heavy**: Auto-balancing and Monte-Carlo testing

## Project Structure

```
QuietStories/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py              # Environment configuration
│   ├── providers/             # LLM provider implementations
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract provider interface
│   │   ├── openai.py         # OpenAI provider
│   │   ├── ollama.py         # Ollama provider
│   │   └── generic.py        # Generic HTTP provider
│   ├── schemas/              # JSON schemas and validation
│   │   ├── __init__.py
│   │   ├── scenario.py       # ScenarioSpec schema
│   │   ├── outcome.py        # Outcome schema
│   │   └── validation.py   # Validation logic
│   ├── engine/               # Core engine components
│   │   ├── __init__.py
│   │   ├── generator.py      # Scenario generation
│   │   ├── validator.py      # Spec validation & auto-balance
│   │   ├── compiler.py       # Spec compilation to tools
│   │   ├── orchestrator.py   # Turn orchestration
│   │   └── memory.py         # Memory management
│   ├── api/                  # FastAPI routes
│   │   ├── __init__.py
│   │   ├── scenarios.py      # Scenario endpoints
│   │   └── sessions.py       # Session endpoints
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── jsonlogic.py      # JSONLogic evaluator
│       └── monte_carlo.py    # Monte Carlo simulation
├── tests/
│   ├── __init__.py
│   ├── test_schemas.py
│   ├── test_validation.py
│   ├── test_monte_carlo.py
│   ├── test_providers.py
│   └── test_integration.py
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## Development Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Core infrastructure and basic functionality

#### Tasks:
1. **Project Setup**
   - Initialize FastAPI project with proper structure
   - Set up dependency management (requirements.txt, pyproject.toml)
   - Configure environment variables and settings
   - Create basic CI/CD pipeline

2. **Provider Interface**
   - Abstract base provider class
   - OpenAI provider implementation
   - Ollama provider implementation
   - Generic HTTP provider
   - Environment-based provider selection

3. **Core Schemas**
   - ScenarioSpec JSON schema (v1.0)
   - Outcome JSON schema with strict validation
   - JSONLogic schema for preconditions/derives
   - EffectOp schemas (set, inc, dec, mul, patch, push, pop, addlog)

#### Acceptance Criteria:
- ✅ Environment-based provider switching works
- ✅ All schemas validate correctly
- ✅ No scenario nouns in codebase

### Phase 2: Core Engine (Weeks 3-4)
**Goal**: Scenario generation and validation

#### Tasks:
1. **Scenario Generator**
   - LLM-based scenario generation from free text
   - System prompt implementation
   - JSON output validation and repair

2. **Validator & Auto-Balance**
   - JSONSchema validation
   - Static bounds checking (weight limits, etc.)
   - Negativity budget enforcement
   - Monte Carlo dry-run simulation
   - Auto-repair mechanism for failed specs

3. **Compiler**
   - Action → tool translation
   - JSONLogic evaluator
   - Effect reducer mapping
   - Tool generation for actions

#### Acceptance Criteria:
- ✅ Generates valid specs from any free-text input
- ✅ Rejects/repairs specs that fail negativity constraints
- ✅ Monte Carlo simulation validates difficulty

### Phase 3: Orchestration (Weeks 5-6)
**Goal**: Turn-based gameplay and memory management

#### Tasks:
1. **Orchestrator**
   - POV-only context building
   - Single model call per turn
   - Tool-enabled LLM calls
   - Outcome validation and repair

2. **Memory System**
   - Public/private memory separation
   - Entity-based memory keys
   - Hidden memory updates
   - Context filtering

3. **Session Management**
   - Session creation and state
   - Turn history tracking
   - SSE streaming for real-time updates

#### Acceptance Criteria:
- ✅ Private thoughts only visible to POV entity
- ✅ Deterministic state changes with same seed
- ✅ Valid Outcome JSON on every turn

### Phase 4: Testing & Polish (Weeks 7-8)
**Goal**: Comprehensive testing and documentation

#### Tasks:
1. **Testing Suite**
   - No-nouns regex test
   - Schema validation tests
   - Monte Carlo property tests
   - Outcome schema tests
   - Determinism tests
   - Visibility enforcement tests

2. **Documentation**
   - API documentation
   - Environment variable guide
   - "No scenario nouns" invariant documentation
   - Usage examples

3. **Performance & Reliability**
   - Error handling and recovery
   - Performance optimization
   - Memory leak prevention
   - Graceful degradation

#### Acceptance Criteria:
- ✅ All tests pass consistently
- ✅ No scenario nouns found in codebase
- ✅ Works with OpenAI and Ollama
- ✅ End-to-end scenarios complete successfully

### Phase 5: Advanced Features (Weeks 9-10)
**Goal**: Enhanced functionality

#### Tasks:
1. **Advanced Effects**
   - Schedule operation (v1.1)
   - Complex state transitions
   - Multi-step effect chains

2. **Enhanced Validation**
   - More sophisticated auto-repair
   - Dynamic difficulty adjustment
   - Advanced Monte Carlo scenarios

3. **Provider Enhancements**
   - Streaming support
   - Retry logic
   - Rate limiting
   - Cost optimization

#### Acceptance Criteria:
- ✅ Advanced scenarios work correctly
- ✅ Auto-repair handles complex cases
- ✅ Performance meets requirements

## Key Technical Challenges & Solutions

### 1. Dynamic Scenario Generation
- **Challenge**: Generate valid, balanced scenarios from any free text
- **Solution**: Robust prompt engineering + auto-repair mechanisms
- **Validation**: Monte Carlo simulation with negativity budget enforcement

### 2. Privacy & Memory Management
- **Challenge**: Prevent "thought leaks" between entities
- **Solution**: Strict POV-only context building + server-side memory updates
- **Validation**: Automated visibility tests

### 3. LLM Provider Abstraction
- **Challenge**: Unified interface for diverse LLM providers
- **Solution**: Abstract base class with provider-specific implementations
- **Validation**: Environment-based switching with consistent behavior

### 4. Auto-Balancing
- **Challenge**: Ensure scenarios aren't too easy or impossible
- **Solution**: Monte Carlo simulation + auto-repair of weights/effects
- **Validation**: Negativity budget enforcement with configurable thresholds

### 5. Deterministic Behavior
- **Challenge**: Reproducible outcomes with seeded RNG
- **Solution**: Deterministic RNG for all random operations
- **Validation**: Same seed + same inputs = same outputs

## Risk Mitigation

### High-Risk Areas:
1. **LLM Output Reliability**: Implement JSON repair mechanisms
2. **Memory Leaks**: Strict context filtering and validation
3. **Performance**: Optimize for single-call-per-turn architecture
4. **Auto-Balancing**: Conservative repair strategies with fallbacks

### Mitigation Strategies:
- Comprehensive test coverage with property-based testing
- Graceful degradation for invalid LLM outputs
- Performance monitoring and optimization
- Extensive documentation of invariants

## Success Metrics

### Functional Requirements:
- ✅ Generates scenarios from any free-text description
- ✅ No scenario nouns in codebase (enforced by tests)
- ✅ Works with OpenAI, Ollama, and generic endpoints
- ✅ Private thoughts only visible to POV entity
- ✅ Deterministic behavior with same seeds

### Quality Requirements:
- ✅ >95% test coverage
- ✅ All schemas validate correctly
- ✅ Monte Carlo simulation validates difficulty
- ✅ Auto-repair handles 90%+ of invalid specs
- ✅ <2s response time per turn

## Implementation Details

### Core Components

#### 1. ScenarioSpec Schema (v1.0)
```json
{
  "spec_version": "1.0",
  "id": "string",
  "name": "string", 
  "seed": "integer",
  "state": "object",
  "entities": "array<object>",
  "actions": "array<object>",
  "random_events": "array<object>",
  "loss_conditions": "array<object>",
  "negativity_budget": "object"
}
```

#### 2. Outcome Schema
```json
{
  "narrative": "string",
  "visible_dialogue": "array<{entity_id, utterance}>",
  "state_changes": "array<{op, path, value}>",
  "roll_requests": "array<{kind, target, difficulty}>",
  "hidden_memory_updates": "array<{scope, target_id, content, visibility}>"
}
```

#### 3. EffectOp Types
- `set { path, value }`
- `inc { path, value }`
- `dec { path, value }`
- `mul { path, value }`
- `patch { path, valueObject }`
- `push { path, value }` / `pop { path }`
- `addlog { message }`
- `schedule { id, at|after, effects[] }` (v1.1)

### API Endpoints

#### Scenario Management
- `POST /scenarios/generate` - Generate scenario from free text
- `POST /scenarios/{id}/compile` - Validate and compile scenario

#### Session Management  
- `POST /sessions` - Create new session
- `GET /sessions/{id}/turns` - Stream turns via SSE

### Environment Configuration

```bash
MODEL_PROVIDER=openai|ollama|generic
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=your_key_here
MODEL_NAME=gpt-4
```

### Testing Strategy

#### 1. No-Nouns Test
- Regex-based scan for disallowed scenario nouns
- Maintain empty list by default
- Build fails if found

#### 2. Schema Tests
- All generated specs must pass JSONSchema validation
- Static bounds checking for weights, etc.

#### 3. Monte Carlo Property Tests
- Random spec sampling within resource bounds
- Dry-run simulation with negativity constraints
- Auto-repair validation

#### 4. Outcome Schema Tests
- Mock provider with malformed payloads
- Ensure repair path catches/fails safely

#### 5. Determinism Tests
- Same seed + same inputs = same state diffs
- Visibility enforcement for non-POV entities

## Next Steps

1. **Immediate**: Set up project structure and basic FastAPI app
2. **Week 1**: Implement provider interface and core schemas
3. **Week 2**: Build scenario generator and validator
4. **Week 3**: Implement orchestrator and memory system
5. **Week 4**: Add comprehensive testing suite
6. **Week 5**: Documentation and performance optimization

This plan provides a comprehensive roadmap for building the Dynamic CYOA Engine while maintaining the strict requirements for dynamic behavior, privacy, and generic implementation.
