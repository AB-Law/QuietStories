# QuietStories

A dynamic Choose-Your-Own-Adventure (CYOA) engine that generates interactive stories using AI. The engine accepts free-text scenario descriptions and automatically creates structured rules, working with both local and remote LLMs through a unified provider interface.

## Features

- **Dynamic Scenario Generation**: Input any free-text description to generate a complete scenario with rules, actions, and events
- **AI-Powered Narrator**: Uses LLMs to create engaging, context-aware story progression
- **Multi-Provider Support**: Works with OpenAI, Ollama, and other OpenAI-compatible endpoints
- **Rule Enforcement**: Server-side validation ensures stories follow generated rules
- **Memory System**: Public and private memory for entities with proper visibility controls
- **Monte Carlo Balancing**: Automatic difficulty balancing through simulation
- **RESTful API**: FastAPI-based backend with comprehensive endpoints
- **React Frontend**: Modern web interface for story interaction
- **Comprehensive Testing**: HTTP-based API testing and debugging tools

## Architecture

The system consists of:

- **Backend** (`backend/`): FastAPI server with scenario generation, compilation, and orchestration
- **Frontend** (`frontend/`): React + TypeScript + Vite web application
- **Engine** (`backend/engine/`): Core logic for scenario validation, compilation, and turn processing
- **Providers** (`backend/providers/`): LLM provider interfaces (OpenAI, Ollama, Generic)
- **Database** (`backend/db/`): SQLite-based data persistence
- **Schemas** (`backend/schemas/`): JSON schemas for validation
- **Utils** (`backend/utils/`): Utilities for logging, debugging, and Monte Carlo simulation

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Ollama (optional, for local LLMs)

### Backend Setup

1. **Clone and navigate to the project:**
   ```bash
   git clone https://github.com/AB-Law/QuietStories.git
   cd QuietStories
   ```

2. **Set up Python environment:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt

   # Copy environment template
   cp random/env.example .env

   # Edit .env with your API keys and settings
   nano .env
   ```

3. **Configure environment variables:**
   ```bash
   # Required
   MODEL_PROVIDER=openai  # or 'ollama' or 'generic'
   OPENAI_API_KEY=your_api_key_here
   MODEL_NAME=gpt-4  # or your preferred model

   # Optional
   LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
   LOG_FILE=logs/app.log  # Optional log file
   ```

4. **Start the backend server:**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

## API Usage

### Generate a Scenario

```bash
curl -X POST "http://localhost:8000/scenarios/generate" \
  -H "Content-Type: application/json" \
  -d '{"description": "A fantasy adventure with dragons and magic"}'
```

### Create a Session

```bash
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "scenario-123", "seed": 42}'
```

### Process a Turn

```bash
curl -X POST "http://localhost:8000/sessions/session-123/turns" \
  -H "Content-Type: application/json" \
  -d '{"action": "explore", "params": {}}'
```

## Testing

The project includes comprehensive testing tools:

### API Testing Script

```bash
# Test scenario generation
python random/api_test.py generate "A fantasy adventure"

# Test complete workflow
python random/api_test.py workflow "Complete test scenario"

# List scenarios
python random/api_test.py list-scenarios
```

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html
```

### Debugging

```bash
# Start server with debug logging
LOG_LEVEL=DEBUG python -m uvicorn backend.main:app --reload

# Run tests with debug output
python random/api_test.py workflow "test" --log-level DEBUG
```

## Development

### Project Structure

```
QuietStories/
├── backend/                 # FastAPI backend
│   ├── api/                # API endpoints
│   ├── engine/             # Core engine logic
│   ├── providers/          # LLM providers
│   ├── db/                 # Database layer
│   ├── schemas/            # JSON schemas
│   └── utils/              # Utilities
├── frontend/               # React frontend
├── tests/                  # Unit tests
├── random/                 # Development tools and docs
└── data/                   # SQLite database
```

### Development Workflow

This project uses automated code quality checks to ensure consistent code standards:

#### Pre-commit Hooks

Pre-commit hooks automatically run code quality checks before each commit:

- **Black**: Code formatting (88 character line length)
- **isort**: Import sorting (compatible with Black)
- **mypy**: Static type checking
- **Frontend Build**: TypeScript compilation and Vite build check

The hooks check both `backend/` and `frontend/` directories as needed.

#### Pre-push Checks

Before pushing code, the following build checks are performed:

- **Backend**: mypy type checking, Black formatting validation, isort import validation
- **Frontend**: TypeScript compilation and Vite build

If any checks fail, the push is blocked until issues are resolved.

#### Setup

After cloning the repository:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# The hooks will now run automatically on commit
# Pre-push checks run automatically on push
```

#### Manual Checks

You can also run checks manually:

```bash
# Backend checks
python -m mypy backend --ignore-missing-imports
python -m black --check backend
python -m isort --check-only backend

# Frontend build
cd frontend && npm run build
```

All these checks are automatically run before each commit via pre-commit hooks.

### Key Concepts

- **ScenarioSpec**: JSON structure defining scenario rules, actions, and events
- **Outcome**: Turn result containing narrative and state changes
- **POV (Point of View)**: Current entity perspective for memory visibility
- **Negativity Budget**: Difficulty balancing mechanism
- **Monte Carlo Simulation**: Automatic scenario balancing

### Adding New Features

1. **New API Endpoint**: Add to `backend/api/`
2. **New Engine Feature**: Add to `backend/engine/`
3. **New Provider**: Implement in `backend/providers/`
4. **New Schema**: Add to `backend/schemas/`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PROVIDER` | LLM provider (openai/ollama/generic) | openai |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `MODEL_NAME` | Model name | gpt-4 |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FILE` | Log file path | - |
| `DATABASE_URL` | Database URL | sqlite:///data/quietstories.db |

### Ollama Setup

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama2`
3. Set environment:
   ```bash
   MODEL_PROVIDER=ollama
   MODEL_NAME=llama2
   ```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Commit with conventional format: `git commit -m "feat: add new feature"`
6. Push and create PR

### Commit Convention

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Testing
- `chore:` - Maintenance

## Troubleshooting

### Common Issues

1. **Server won't start**: Check Python version (3.11+) and dependencies
2. **API connection failed**: Ensure backend is running on port 8000
3. **LLM errors**: Check API keys and model availability
4. **Database errors**: Ensure `data/` directory exists and is writable

### Debug Mode

```bash
# Start with detailed logging
LOG_LEVEL=DEBUG python -m uvicorn backend.main:app --reload

# Use VSCode debugger (F5) for breakpoints
```

### Logs

Check logs in:
- Console output (when running server)
- `logs/app.log` (if configured)
- Test output with `--log-level DEBUG`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with FastAPI, React, and modern Python tooling
- Inspired by interactive fiction and AI storytelling
- Thanks to the open-source community for amazing tools</content>
<parameter name="filePath">/Users/akshayb/projects/QuietStories/README.md
# Test comment
