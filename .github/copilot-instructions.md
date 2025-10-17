# GitHub Copilot Instructions for QuietStories

## Project Overview

QuietStories is a dynamic Choose-Your-Own-Adventure (CYOA) engine that generates interactive stories using AI. The system accepts free-text scenario descriptions and automatically creates structured rules, working with both local and remote LLMs through a unified provider interface.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite with SQLAlchemy ORM
- **AI/LLM**: LangChain, OpenAI SDK, LangGraph
- **Vector Store**: ChromaDB for semantic memory search
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Code Quality**: Black (formatter), isort (import sorting), mypy (type checking)

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS v4 with typography plugin
- **Routing**: React Router v7
- **UI Components**: Lucide React icons, class-variance-authority

## Code Style and Quality

### Python Backend
- Follow PEP 8 style guide with 88-character line length (Black default)
- Use type hints for all function parameters and return values
- Write docstrings following PEP 257 conventions
- Run code quality tools before committing:
  - `python -m black backend` - Format code
  - `python -m isort backend --profile black` - Sort imports
  - `python -m mypy backend --ignore-missing-imports` - Type checking
- Use the `typing` module for complex types (List, Dict, Optional, etc.)
- Handle exceptions explicitly with clear error messages
- Break down complex functions into smaller, manageable pieces

### TypeScript/React Frontend
- Use TypeScript for all new files with proper type annotations
- Follow React 19 best practices and hooks patterns
- Use functional components with hooks (no class components)
- Organize imports: React imports first, then third-party, then local
- Use TailwindCSS for styling (avoid inline styles when possible)
- Component file structure: imports, types/interfaces, component, export

## Project Structure

```
QuietStories/
├── backend/
│   ├── api/          # FastAPI route handlers
│   ├── engine/       # Core scenario engine logic
│   ├── providers/    # LLM provider interfaces (OpenAI, Ollama, LMStudio)
│   ├── db/           # Database models and managers
│   ├── schemas/      # JSON schemas for validation
│   ├── utils/        # Logging, debugging, utilities
│   └── main.py       # FastAPI application entry point
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom React hooks
│   │   └── types/       # TypeScript type definitions
│   └── package.json
└── .github/
    └── instructions/    # Specific coding instructions
```

## Key Architectural Concepts

### Backend Concepts
- **ScenarioSpec**: JSON structure defining scenario rules, actions, and events
- **Outcome**: Turn result containing narrative and state changes
- **POV (Point of View)**: Current entity perspective for memory visibility
- **Provider Pattern**: Unified interface for multiple LLM providers (OpenAI, Ollama, LMStudio)
- **Memory System**: Public and private memories with semantic search via embeddings

### API Design
- RESTful endpoint design following FastAPI conventions
- Use Pydantic models for request/response validation
- Include proper HTTP status codes and error handling
- Document endpoints with OpenAPI descriptions

## Git and Commit Conventions

- **Branch naming**: Use `feature/`, `bugfix/`, or `chore/` prefixes
  - Example: `feature/add-user-auth`, `bugfix/fix-login-error`, `chore/update-deps`
- **Commit messages**: Follow conventional commits format (NO emojis)
  - `feat:` - New features
  - `fix:` - Bug fixes
  - `chore:` - Maintenance tasks
  - `docs:` - Documentation changes
  - `test:` - Test additions or modifications
  - `refactor:` - Code refactoring
  - Example: `feat: add semantic memory search`, `fix: resolve null pointer in chat`
- **Atomic commits**: One logical change per commit
- **Reference issues**: Use `Closes #123` or `Relates to #456` in commit messages

## Testing Guidelines

### Backend Testing
- Write pytest tests for new API endpoints and engine features
- Use pytest-asyncio for async endpoint tests
- Include edge cases: empty inputs, invalid data, large datasets
- Test both success and error paths
- Run tests with: `pytest` or `pytest --cov=backend --cov-report=html`
- Mock external API calls (LLM providers) in tests

### Frontend Testing
- Test critical user interactions and state management
- Ensure TypeScript compilation passes: `npm run build`
- Check linting: `npm run lint`

## LLM Provider Integration

When working with LLM provider code:
- All providers must implement the common interface pattern
- Support for multiple backends: OpenAI API, Ollama, LMStudio
- Handle API errors gracefully with retry logic
- Include appropriate timeouts for LLM calls
- Log provider interactions for debugging
- Support both streaming and non-streaming responses
- Test with mock responses to avoid API costs

## Environment and Configuration

- Use environment variables for configuration (MODEL_PROVIDER, API keys, etc.)
- Never commit secrets or API keys
- Support both local and cloud LLM deployments
- Document any new environment variables in README.md

## Documentation Requirements

- Update README.md for user-facing changes
- Add comments for complex logic or algorithms
- Document API changes in docstrings
- Update relevant guides (LMSTUDIO_SETUP.md, LOCAL_EMBEDDINGS.md, OPTIMIZATION_GUIDE.md)
- Include examples in docstrings when helpful

## Pre-commit Hooks

The repository uses pre-commit hooks that automatically run:
- Black formatting
- isort import sorting  
- mypy type checking
- Frontend TypeScript build

**Never bypass these checks** - they ensure code quality and CI/CD success.

## CI/CD Requirements

- All code must pass CI checks before merging
- Fix all mypy type errors before pushing
- Ensure Black and isort formatting compliance
- Frontend must build successfully without errors
- All tests must pass

## Security Best Practices

- Validate all user inputs
- Sanitize data before database operations
- Use parameterized queries (SQLAlchemy handles this)
- Don't expose internal error details to users
- Follow principle of least privilege
- Review code for common vulnerabilities (SQL injection, XSS, etc.)

## Additional Context

- The project supports fully local deployments (no cloud dependencies)
- Semantic memory search uses ChromaDB with embeddings
- The scenario engine uses JSON schemas for validation
- Monte Carlo simulation for automatic scenario balancing
- Docker Compose available for easy deployment

## Reference Documentation

For more detailed guidance, see:
- `.github/instructions/python.instructions.md` - Python-specific coding standards
- `.github/instructions/git-strategy.instructions.md` - Git workflow details
- `CONTRIBUTING.md` - Contribution guidelines and development workflow
- `README.md` - Project setup and architecture overview
- `LMSTUDIO_SETUP.md` - Local LLM setup guide
- `OPTIMIZATION_GUIDE.md` - Performance optimization tips

## When Suggesting Changes

1. Understand the context by reading relevant documentation
2. Follow existing patterns and conventions in the codebase
3. Make minimal, focused changes
4. Test your changes locally
5. Run all quality checks (Black, isort, mypy, tests)
6. Update documentation if needed
7. Write clear, descriptive commit messages
8. Reference related issues in commits and PRs

## Common Pitfalls to Avoid

- Don't bypass pre-commit hooks or CI/CD checks
- Don't use emojis in commit messages
- Don't commit without running Black, isort, and mypy
- Don't add dependencies without discussing first
- Don't modify working code unnecessarily
- Don't remove or skip existing tests
- Don't hard-code configuration values (use environment variables)
- Don't expose API keys or secrets in code
