# QuietStories

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A dynamic Choose-Your-Own-Adventure (CYOA) engine that generates interactive stories using AI. The engine accepts free-text scenario descriptions and automatically creates structured rules, working with both local and remote LLMs through a unified provider interface.

## Features

- **Dynamic Scenario Generation**: Input any free-text description to generate a complete scenario with rules, actions, and events
- **AI-Powered Narrator**: Uses LLMs to create engaging, context-aware story progression
- **Multi-Provider Support**: Works with OpenAI, Ollama, LMStudio, and other OpenAI-compatible endpoints
- **Local LLM Support**: Full support for running models locally via LMStudio or Ollama
- **Local Embeddings**: Run semantic memory search completely locally without OpenAI API
- **Smart Optimization**: Automatic context reduction, memory consolidation, and caching for faster performance
- **Rule Enforcement**: Server-side validation ensures stories follow generated rules
- **Memory System**: Public and private memory for entities with proper visibility controls
- **Semantic Memory Search**: Find relevant memories by meaning, not just keywords
- **Monte Carlo Balancing**: Automatic difficulty balancing through simulation
- **RESTful API**: FastAPI-based backend with comprehensive endpoints
- **React Frontend**: Modern web interface for story interaction
- **Comprehensive Testing**: HTTP-based API testing and debugging tools

## 📚 Documentation

- **[LM Studio Setup Guide](./LMSTUDIO_SETUP.md)** - Complete guide for running QuietStories with LM Studio locally
- **[Local Embeddings Guide](./LOCAL_EMBEDDINGS.md)** - Set up local embeddings for semantic memory search
- **[Optimization Guide](./OPTIMIZATION_GUIDE.md)** - Performance tips and local LLM configuration
- **[Logging Guide](./LOGGING.md)** - Centralized logging and monitoring setup
- **[Grafana Integration](./GRAFANA_INTEGRATION.md)** - Observability stack for production monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   LLM APIs      │
│   (React/Vite)  │◄──►│   (FastAPI)     │◄──►│   (OpenAI/      │
│                 │    │                 │    │    Ollama/      │
│   - Chat UI     │    │   - REST API    │    │    LMStudio)    │
│   - Admin Panel │    │   - Scenario    │    │                 │
│   - State Mgmt  │    │     Engine      │    │   - Embeddings  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Database      │
                    │   (SQLite)      │
                    │                 │
                    │   - Scenarios   │
                    │   - Sessions    │
                    │   - Memories    │
                    └─────────────────┘
```

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
- **For Local LLMs**: Ollama or LM Studio (see setup guides below)
- **For Semantic Search**: ChromaDB (optional, for memory search)

> **🚀 Running Completely Local?**
> - Follow the **[LM Studio Setup Guide](./LMSTUDIO_SETUP.md)** for step-by-step instructions
> - See **[Local Embeddings Guide](./LOCAL_EMBEDDINGS.md)** to enable semantic memory search locally
> - No OpenAI API key required!

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
   cp .env.example .env

   # Edit .env with your API keys and settings
   nano .env
   ```

3. **Configure environment variables:**
   ```bash
   # For OpenAI (cloud)
   MODEL_PROVIDER=openai
   OPENAI_API_KEY=your_api_key_here
   MODEL_NAME=gpt-4o-mini

   # For LM Studio (local) - See LMSTUDIO_SETUP.md for complete guide
   MODEL_PROVIDER=lmstudio
   LMSTUDIO_API_BASE=http://localhost:1234/v1
   MODEL_NAME=llama-3.2-3b-instruct

   # For Ollama (local)
   MODEL_PROVIDER=ollama
   OPENAI_API_BASE=http://localhost:11434/v1
   MODEL_NAME=llama3.2:3b

   # Optional: Local embeddings for semantic memory search
   EMBEDDING_PROVIDER=ollama  # or 'lmstudio' or 'none'
   EMBEDDING_MODEL_NAME=nomic-embed-text

   # Logging (optional)
   LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
   LOG_FILE=logs/app.log
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

## Docker Quickstart

For the easiest way to run QuietStories, use Docker Compose:

```bash
# Clone the repository
git clone https://github.com/AB-Law/QuietStories.git
cd QuietStories

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and settings

# Start all services (API, frontend, and optional logging)
docker-compose up

# Or start just the API and frontend
docker-compose --profile full up
```

The application will be available at:
- **API**: `http://localhost:8000`
- **Frontend**: `http://localhost:5173`
- **API Documentation**: `http://localhost:8000/docs`

### Docker Services

- `api`: FastAPI backend server
- `web`: React frontend application
- `chroma`: ChromaDB for semantic memory (optional)
- `loki`, `grafana`, `promtail`: Logging and monitoring stack (optional)

### Production Deployment

For production deployment, use the provided Docker images:

```bash
# Pull the latest images
docker pull ghcr.io/ab-law/quietstories-api:latest
docker pull ghcr.io/ab-law/quietstories-web:latest

# Run with docker-compose (update the compose file for production settings)
docker-compose -f docker-compose.prod.yml up
```

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

### Local LLM Setup

#### Option 1: LMStudio (Recommended for beginners)

1. Download LMStudio: https://lmstudio.ai/
2. Load a model (e.g., Mistral 7B)
3. Start the local server
4. Configure:
   ```bash
   MODEL_PROVIDER=lmstudio
   OPENAI_API_BASE=http://localhost:5101/v1
   MODEL_NAME=local-model
   ```

#### Option 2: Ollama

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama2`
3. Set environment:
   ```bash
   MODEL_PROVIDER=ollama
   MODEL_NAME=llama2
   ```

**For detailed setup and optimization:** See [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md)

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
