# Release Process Setup - Implementation Summary

This document summarizes the release process and dev branch implementation for QuietStories.

## Overview

A comprehensive release workflow has been implemented that enables:
- ✅ Two-branch workflow (main for production, dev for development)
- ✅ Automated Docker image building for both branches
- ✅ One-command deployment script
- ✅ Complete documentation for releases and deployment
- ✅ Environment configuration examples

## What Was Implemented

### 1. Branching Strategy

**Main Branch (`main`)**
- Production-ready, stable releases only
- Protected branch requiring PR reviews
- Docker images tagged as `latest`
- All releases are tagged from this branch (e.g., v1.0.0)

**Development Branch (`dev`)**
- Integration branch for active development
- Feature branches merge here first
- Docker images tagged as `dev`
- Must pass all CI/CD checks

**Feature Branches**
- Naming convention: `feature/name`, `bugfix/name`, `chore/name`
- Created from `dev`
- Merged back to `dev` via pull request
- Deleted after merge

### 2. CI/CD Pipeline Updates

**File:** `.github/workflows/ci.yml`

Changes:
- Added `dev` branch to trigger list (alongside `main`)
- Workflow now runs on PRs and pushes to both branches
- Docker images built with appropriate tags:
  - `latest` for main branch
  - `dev` for dev branch
  - `v1.0.0` for version tags
  - `main-<sha>` and `dev-<sha>` for commit-specific builds

### 3. Production Deployment

**File:** `docker-compose.prod.yml`

A production-ready Docker Compose configuration that:
- Uses pre-built images from GitHub Container Registry
- Includes API, frontend, and ChromaDB services
- Configures health checks and restart policies
- Manages volumes for persistent data
- Documents environment variables inline

Services:
- `api`: FastAPI backend (port 8000)
- `web`: React frontend (port 80)
- `chroma`: ChromaDB vector store (port 8001)

### 4. Deployment Script

**File:** `scripts/deploy.sh`

One-command deployment with features:
- Tag selection (latest, dev, v1.0.0)
- Image pulling control
- Service management (start, stop, restart, down)
- Log viewing (static or follow)
- Health checks after deployment

Usage examples:
```bash
./scripts/deploy.sh                  # Deploy latest stable
./scripts/deploy.sh --tag dev        # Deploy dev version
./scripts/deploy.sh --tag v1.0.0     # Deploy specific version
./scripts/deploy.sh --pull --logs    # Pull and view logs
```

### 5. Documentation

**New Files:**

1. **RELEASE.md** - Complete release process guide
   - Branching strategy details
   - Semantic versioning guidelines
   - Step-by-step release workflow
   - Docker image tagging strategy
   - Deployment options (Docker, local, manual)
   - Environment configuration guide
   - Troubleshooting section

2. **QUICKSTART.md** - Fast onboarding guide
   - 3-step production deployment
   - Local development setup
   - Local LLM configuration (LM Studio/Ollama)
   - Cloud deployment (OpenAI)
   - Common commands
   - Troubleshooting

3. **.env.example** - Environment configuration template
   - All provider options (OpenAI, LM Studio, Ollama)
   - Production and development settings
   - Docker-specific configurations
   - Inline documentation

**Updated Files:**

1. **README.md**
   - Added branching strategy section
   - Updated deployment section
   - Added QuickStart guide link
   - Referenced RELEASE.md

2. **CONTRIBUTING.md**
   - Updated to reflect dev branch workflow
   - Clear instructions for contributors
   - PR process targeting dev branch

3. **.gitignore**
   - Allowed .env.example while ignoring other .env files

## How to Use

### For Development

1. **Create feature branch from dev:**
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/my-feature
   ```

2. **Make changes, test, commit:**
   ```bash
   # Make your changes
   git commit -m "feat: add new feature"
   ```

3. **Push and create PR to dev:**
   ```bash
   git push origin feature/my-feature
   # Create PR targeting dev branch
   ```

4. **After merge, CI/CD automatically builds dev images**

### For Production Release

1. **Prepare release from dev to main:**
   ```bash
   git checkout dev
   git pull origin dev
   
   # Update CHANGELOG.md if exists
   # Verify all tests pass
   
   git checkout main
   git pull origin main
   git merge dev
   ```

2. **Tag the release:**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin main
   git push origin v1.0.0
   ```

3. **CI/CD automatically:**
   - Runs all tests
   - Builds Docker images
   - Tags with v1.0.0 and latest
   - Publishes to GitHub Container Registry

4. **Sync dev with main:**
   ```bash
   git checkout dev
   git merge main
   git push origin dev
   ```

### For Deployment

**Production (using latest stable):**
```bash
git clone https://github.com/AB-Law/QuietStories.git
cd QuietStories
cp .env.example .env
# Edit .env with your settings
./scripts/deploy.sh
```

**Testing dev branch:**
```bash
./scripts/deploy.sh --tag dev
```

**Specific version:**
```bash
./scripts/deploy.sh --tag v1.0.0
```

## Docker Images

Images are published to GitHub Container Registry:

**Backend API:**
- `ghcr.io/ab-law/quietstories-api:latest` (main branch)
- `ghcr.io/ab-law/quietstories-api:dev` (dev branch)
- `ghcr.io/ab-law/quietstories-api:v1.0.0` (releases)

**Frontend Web:**
- `ghcr.io/ab-law/quietstories-web:latest` (main branch)
- `ghcr.io/ab-law/quietstories-web:dev` (dev branch)
- `ghcr.io/ab-law/quietstories-web:v1.0.0` (releases)

## Next Steps

1. **Create dev branch:**
   ```bash
   git checkout -b dev main
   git push origin dev
   ```

2. **Set up branch protections** (in GitHub):
   - Protect `main` branch: require PR reviews
   - Protect `dev` branch: require CI/CD to pass

3. **Create first release:**
   - When ready, tag v1.0.0 from main
   - Docker images will automatically build

4. **Update documentation:**
   - Add to CHANGELOG.md as features are added
   - Document breaking changes

## Testing

All quality checks pass:
- ✅ Backend tests: 10/10 passing
- ✅ Frontend build: Successful
- ✅ Black formatting: Compliant
- ✅ isort imports: Compliant
- ✅ Deployment script: Syntax validated

## Files Changed/Created

**Created:**
- `.env.example` - Environment configuration template
- `QUICKSTART.md` - Quick start guide
- `RELEASE.md` - Complete release documentation
- `docker-compose.prod.yml` - Production deployment config
- `scripts/deploy.sh` - Deployment automation script

**Modified:**
- `.github/workflows/ci.yml` - Added dev branch support
- `.gitignore` - Allow .env.example
- `CONTRIBUTING.md` - Updated workflow
- `README.md` - Added branching and deployment info

## Support Resources

- **QUICKSTART.md** - Get started in minutes
- **RELEASE.md** - Detailed release process
- **CONTRIBUTING.md** - Contribution guidelines
- **README.md** - Project overview
- **LMSTUDIO_SETUP.md** - Local LLM setup

## Summary

The implementation provides:
1. ✅ Clear branching strategy (main/dev/feature)
2. ✅ Automated CI/CD for both branches
3. ✅ Production-ready Docker deployment
4. ✅ One-command deployment script
5. ✅ Comprehensive documentation
6. ✅ Environment configuration examples
7. ✅ Quick start guide for users

**Everything is ready for immediate use!** 🚀
