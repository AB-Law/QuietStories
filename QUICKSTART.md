# QuickStart Guide

Get QuietStories running in minutes with this quick reference.

## 🚀 Production Deployment (Docker)

The fastest way to run QuietStories in production:

```bash
# 1. Clone the repository
git clone https://github.com/AB-Law/QuietStories.git
cd QuietStories

# 2. Create environment configuration
cp .env.example .env
# Edit .env with your API keys and settings

# 3. Deploy with one command
./scripts/deploy.sh
```

That's it! QuietStories is now running:
- **Frontend**: http://localhost
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Using Different Versions

```bash
# Use dev version (latest development)
./scripts/deploy.sh --tag dev

# Use specific release
./scripts/deploy.sh --tag v1.0.0
```

## 🛠️ Local Development Setup

For development with hot-reloading:

### Backend

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Create .env file
cp .env.example .env
# Configure for local LLM (LM Studio/Ollama) or OpenAI

# 3. Start backend server
python -m uvicorn backend.main:app --reload
```

API available at: http://localhost:8000

### Frontend

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# 4. Start development server
npm run dev
```

Frontend available at: http://localhost:5173

## 🤖 Local LLM Setup (No API Key Required)

Run QuietStories completely locally with LM Studio or Ollama:

### Option 1: LM Studio

```bash
# 1. Download and start LM Studio
# See: https://lmstudio.ai/

# 2. Load a model (e.g., llama-3.2-3b-instruct)

# 3. Start local server (port 1234)

# 4. Configure .env
MODEL_PROVIDER=lmstudio
LMSTUDIO_API_BASE=http://localhost:1234/v1
MODEL_NAME=llama-3.2-3b-instruct
EMBEDDING_PROVIDER=lmstudio
EMBEDDING_MODEL_NAME=nomic-embed-text

# 5. Start QuietStories
python -m uvicorn backend.main:app --reload
```

### Option 2: Ollama

```bash
# 1. Install Ollama
# See: https://ollama.ai/

# 2. Pull a model
ollama pull llama3.2:3b

# 3. Configure .env
MODEL_PROVIDER=ollama
OPENAI_API_BASE=http://localhost:11434/v1
MODEL_NAME=llama3.2:3b
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_NAME=nomic-embed-text

# 4. Start QuietStories
python -m uvicorn backend.main:app --reload
```

For detailed setup, see [LMSTUDIO_SETUP.md](./LMSTUDIO_SETUP.md)

## ☁️ Cloud Deployment (OpenAI)

Using OpenAI for cloud-based LLM:

```bash
# 1. Get OpenAI API key from https://platform.openai.com/

# 2. Configure .env
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-...your-key-here...
MODEL_NAME=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-small

# 3. Deploy
./scripts/deploy.sh
```

## 📋 Common Commands

### Docker Deployment

```bash
# Start services
./scripts/deploy.sh

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
./scripts/deploy.sh --down

# Restart services
./scripts/deploy.sh --restart

# Update to latest version
./scripts/deploy.sh --pull
```

### Local Development

```bash
# Backend
python -m uvicorn backend.main:app --reload

# Frontend
cd frontend && npm run dev

# Run tests
pytest backend/tests/ -v

# Format code
python -m black backend
python -m isort backend --profile black
```

## 🔍 Verification

After starting QuietStories, verify it's working:

1. **API Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Open Frontend**: Navigate to http://localhost (or http://localhost:5173 for dev)

3. **Check API Docs**: http://localhost:8000/docs

4. **Create a Test Scenario**:
   ```bash
   curl -X POST "http://localhost:8000/scenarios/generate" \
     -H "Content-Type: application/json" \
     -d '{"description": "A fantasy adventure with dragons"}'
   ```

## 📚 Next Steps

- **Development**: Read [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Release Process**: See [RELEASE.md](./RELEASE.md)
- **Local LLM Guide**: Check [LMSTUDIO_SETUP.md](./LMSTUDIO_SETUP.md)
- **Performance Tips**: Review [OPTIMIZATION_GUIDE.md](./OPTIMIZATION_GUIDE.md)

## 🆘 Troubleshooting

### Port Conflicts

If ports 80, 8000, or 8001 are already in use:

```bash
# Edit docker-compose.prod.yml
# Change port mappings, e.g., "8080:80" instead of "80:80"
```

### Docker Issues

```bash
# Ensure Docker is running
docker info

# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# View logs for errors
docker-compose -f docker-compose.prod.yml logs
```

### LM Studio Connection

```bash
# Ensure LM Studio server is running on port 1234
# For Docker, use host.docker.internal:1234
curl http://localhost:1234/v1/models
```

### API Connection from Frontend

1. Check `VITE_API_URL` in frontend `.env` file
2. For Docker deployment, use `http://localhost:8000`
3. Ensure API is accessible from your browser

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/AB-Law/QuietStories/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AB-Law/QuietStories/discussions)
- **Documentation**: [README.md](./README.md)
