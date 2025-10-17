# Release Process and Deployment Guide

This guide documents the release process, branching strategy, and deployment procedures for QuietStories.

## Table of Contents

- [Branching Strategy](#branching-strategy)
- [Version Management](#version-management)
- [Release Workflow](#release-workflow)
- [Docker Images](#docker-images)
- [Deployment Options](#deployment-options)
- [Quick Start Deployment](#quick-start-deployment)
- [Environment Configuration](#environment-configuration)

## Branching Strategy

QuietStories follows a **two-branch** workflow:

### Main Branch (`main`)
- **Purpose**: Production-ready, stable releases
- **Stability**: All code must pass CI/CD checks
- **Docker Tags**: `latest` tag points to the latest main commit
- **Protection**: Requires pull request reviews before merging
- **Releases**: Tagged releases (v1.0.0, v1.1.0, etc.) are created from main

### Development Branch (`dev`)
- **Purpose**: Integration branch for active development
- **Stability**: Must pass CI/CD tests but may have experimental features
- **Docker Tags**: `dev` tag for testing unreleased features
- **Workflow**: Feature branches merge into `dev`, then `dev` merges into `main` for releases
- **Testing**: Use this branch to test upcoming features before production

### Feature Branches
- **Naming**: `feature/feature-name`, `bugfix/bug-name`, or `chore/task-name`
- **Base**: Created from `dev`
- **Target**: Merged back into `dev` via pull request
- **Lifecycle**: Deleted after merge

### Release Flow

```
feature/new-feature → dev → main (tagged as v1.x.x) → production
```

## Version Management

QuietStories uses **Semantic Versioning** (SemVer):

### Version Format: `MAJOR.MINOR.PATCH`

- **MAJOR** (v2.0.0): Breaking changes, incompatible API changes
- **MINOR** (v1.1.0): New features, backward-compatible
- **PATCH** (v1.0.1): Bug fixes, backward-compatible

### Release Candidates

For testing before stable releases:
- Format: `v1.0.0-rc1`, `v1.0.0-rc2`
- Used for pre-release testing
- Docker images tagged with the RC version

### How to Version

1. **Determine version bump**:
   - Breaking changes → bump MAJOR
   - New features → bump MINOR
   - Bug fixes → bump PATCH

2. **Update version references** (if applicable):
   - README.md examples
   - CHANGELOG.md (create entries for what's changed)

3. **Create and push tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

## Release Workflow

### Step 1: Develop on `dev` Branch

```bash
# Create feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/my-feature

# Make changes, commit with conventional commits
git commit -m "feat: add new feature"

# Push and create PR to dev
git push origin feature/my-feature
```

### Step 2: Merge to `dev`

1. Create pull request from `feature/my-feature` to `dev`
2. Ensure CI/CD passes (tests, linting, builds)
3. Get code review approval
4. Merge PR
5. `dev` branch Docker images are automatically built

### Step 3: Release from `dev` to `main`

When ready for a production release:

```bash
# Ensure dev is up to date
git checkout dev
git pull origin dev

# Create release branch (optional, for final testing)
git checkout -b release/v1.0.0

# Update CHANGELOG.md with release notes
# Make any final adjustments

# Merge to main
git checkout main
git pull origin main
git merge dev  # or merge release/v1.0.0

# Create and push tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin main
git push origin v1.0.0

# Sync dev with main
git checkout dev
git merge main
git push origin dev
```

### Step 4: Monitor CI/CD

The GitHub Actions workflow will automatically:
1. Run quality checks (pre-commit hooks)
2. Run backend tests
3. Build and test frontend
4. Build and push Docker images with tags:
   - `latest` (for main branch)
   - `dev` (for dev branch)
   - `v1.0.0` (for version tags)
   - `v1.0` (major.minor tags)
   - `main-<sha>` or `dev-<sha>` (commit-specific)

## Docker Images

QuietStories publishes two Docker images to GitHub Container Registry:

### Backend API
```
ghcr.io/ab-law/quietstories-api:latest
ghcr.io/ab-law/quietstories-api:dev
ghcr.io/ab-law/quietstories-api:v1.0.0
```

### Frontend Web
```
ghcr.io/ab-law/quietstories-web:latest
ghcr.io/ab-law/quietstories-web:dev
ghcr.io/ab-law/quietstories-web:v1.0.0
```

### Pulling Images

```bash
# Pull latest stable (from main)
docker pull ghcr.io/ab-law/quietstories-api:latest
docker pull ghcr.io/ab-law/quietstories-web:latest

# Pull dev version (from dev branch)
docker pull ghcr.io/ab-law/quietstories-api:dev
docker pull ghcr.io/ab-law/quietstories-web:dev

# Pull specific version
docker pull ghcr.io/ab-law/quietstories-api:v1.0.0
docker pull ghcr.io/ab-law/quietstories-web:v1.0.0
```

## Deployment Options

### Option 1: Docker Compose (Production - Recommended)

Use the pre-built Docker images:

```bash
# Clone the repository for docker-compose.prod.yml
git clone https://github.com/AB-Law/QuietStories.git
cd QuietStories

# Create necessary directories
mkdir -p data logs

# (Optional) Create .env file for configuration
cp .env.example .env

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

Services will be available at:
- **Frontend**: http://localhost (port 80)
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8001

### Option 2: Local Development

For development with hot-reloading:

```bash
# Backend
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

### Option 3: Manual Docker Run

```bash
# Run backend
docker run -d \
  --name quietstories-api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  ghcr.io/ab-law/quietstories-api:latest

# Run frontend
docker run -d \
  --name quietstories-web \
  -p 80:80 \
  -e VITE_API_URL=http://localhost:8000 \
  ghcr.io/ab-law/quietstories-web:latest
```

## Quick Start Deployment

Use the provided deployment script for one-command setup:

```bash
# Deploy with latest stable version
./scripts/deploy.sh

# Deploy with dev version
./scripts/deploy.sh --tag dev

# Deploy with specific version
./scripts/deploy.sh --tag v1.0.0
```

See the script for available options and customization.

## Environment Configuration

### Production Environment Variables

Create a `.env` file in the project root:

```bash
# LLM Provider Configuration
MODEL_PROVIDER=openai              # openai, lmstudio, ollama
MODEL_NAME=gpt-4o-mini             # Model name

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=your_api_key_here

# Local LLM Configuration (if using LMStudio/Ollama)
LMSTUDIO_API_BASE=http://host.docker.internal:1234/v1
OPENAI_API_BASE=http://host.docker.internal:11434/v1

# Embedding Configuration
EMBEDDING_PROVIDER=openai          # openai, ollama, lmstudio, none
EMBEDDING_MODEL_NAME=text-embedding-3-small

# Database
DATABASE_PATH=/app/data/quietstories.db

# Logging
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
ENABLE_CONSOLE_LOGS=false          # true for dev, false for prod

# Frontend API URL (for browser access)
VITE_API_URL=http://localhost:8000 # Change to your domain in production
```

### Local Development with LM Studio

See [LMSTUDIO_SETUP.md](./LMSTUDIO_SETUP.md) for complete local LLM setup.

```bash
# .env for local development with LM Studio
MODEL_PROVIDER=lmstudio
LMSTUDIO_API_BASE=http://localhost:1234/v1
MODEL_NAME=llama-3.2-3b-instruct
EMBEDDING_PROVIDER=lmstudio
EMBEDDING_MODEL_NAME=nomic-embed-text
```

## CI/CD Pipeline

The CI/CD pipeline automatically runs on:
- **Pull Requests** to `main` or `dev`: Runs tests and builds
- **Pushes** to `main` or `dev`: Runs tests, builds, and publishes Docker images
- **Tags** (v*, v*-rc*): Runs tests, builds, and publishes versioned images

### Pipeline Stages

1. **Quality**: Pre-commit hooks (Black, isort, mypy)
2. **Backend**: Python tests with pytest
3. **Frontend**: Linting and build with npm
4. **Docker**: Build and push images to GitHub Container Registry

### Viewing CI/CD Status

Check the [Actions tab](https://github.com/AB-Law/QuietStories/actions) in GitHub for:
- Build status
- Test results
- Docker image publication

## Troubleshooting

### Docker Images Not Updating

```bash
# Force pull latest images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Port Conflicts

If ports 80, 8000, or 8001 are in use:

```bash
# Edit docker-compose.prod.yml to change port mappings
# For example, change "80:80" to "8080:80"
```

### API Connection Issues

1. Check that `VITE_API_URL` matches where your API is accessible
2. For Docker, use `http://localhost:8000`
3. For production, use your domain: `https://api.yourdomain.com`

## Additional Resources

- [README.md](./README.md) - Project overview and quick start
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [LMSTUDIO_SETUP.md](./LMSTUDIO_SETUP.md) - Local LLM setup guide
- [frontend/FRONTEND_README.md](./frontend/FRONTEND_README.md) - Frontend documentation

## Support

For issues, questions, or contributions:
- [GitHub Issues](https://github.com/AB-Law/QuietStories/issues)
- [GitHub Discussions](https://github.com/AB-Law/QuietStories/discussions)
