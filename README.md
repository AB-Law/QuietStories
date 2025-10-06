# Dynamic CYOA Engine

A Python-based engine that generates dynamic Choose Your Own Adventure scenarios from free-text descriptions, with no hardcoded scenario nouns, supporting both local and remote LLMs through a unified interface.

## Features

- **Dynamic Scenario Generation**: Generate scenarios from any free-text description
- **LLM Agnostic**: Works with OpenAI, Ollama, and generic endpoints
- **Privacy-First**: Prevents "thought leaks" between entities
- **Auto-Balancing**: Monte Carlo simulation for difficulty validation
- **No Hardcoded Content**: Zero scenario nouns in codebase

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd QuietStories

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp env.example .env
```

### Configuration

Edit `.env` file with your LLM provider settings:

```bash
# For OpenAI
MODEL_PROVIDER=openai
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4

# For Ollama (local)
MODEL_PROVIDER=ollama
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=dummy_key
MODEL_NAME=llama2
```

### Running the Server

```bash
# Start the FastAPI server
python -m src.main

# Or with uvicorn directly
uvicorn src.main:app --reload
```

### API Usage

#### Generate a Scenario

```bash
curl -X POST "http://localhost:8000/scenarios/generate" \
  -H "Content-Type: application/json" \
  -d '{"description": "A space adventure where you must escape from an alien planet"}'
```

#### Compile a Scenario

```bash
curl -X POST "http://localhost:8000/scenarios/{scenario_id}/compile" \
  -H "Content-Type: application/json" \
  -d '{"spec": {...}}'
```

#### Create a Session

```bash
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "scenario_id", "seed": 12345}'
```

#### Stream Turns

```bash
curl -X GET "http://localhost:8000/sessions/{session_id}/turns"
```

## Architecture

### Core Components

- **Providers**: LLM provider abstraction (OpenAI, Ollama, Generic)
- **Schemas**: JSON schemas for ScenarioSpec and Outcome validation
- **Engine**: Scenario generation, validation, compilation, and orchestration
- **API**: FastAPI routes for scenarios and sessions
- **Memory**: Private/public memory management for entities

### Key Principles

1. **Dynamic Only**: No hand-written rulepacks or scenario nouns in code
2. **Generic Engine**: Works with any scenario description
3. **LLM Agnostic**: Unified interface for all providers
4. **Privacy-First**: POV-only memory visibility
5. **Validation-Heavy**: Auto-balancing and Monte Carlo testing

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_schemas.py
pytest tests/test_no_nouns.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

[Add your license here]