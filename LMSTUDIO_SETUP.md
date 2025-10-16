# LM Studio Setup Guide for QuietStories

This guide walks you through setting up LM Studio to run QuietStories completely locally.

**See also:** [Local Embeddings Guide](./LOCAL_EMBEDDINGS.md) for semantic memory search setup.

## Table of Contents

1. [What is LM Studio?](#what-is-lm-studio)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Downloading Models](#downloading-models)
5. [Starting the Server](#starting-the-server)
6. [Configuring QuietStories](#configuring-quietstories)
7. [Testing the Connection](#testing-the-connection)
8. [Troubleshooting](#troubleshooting)
9. [Recommended Models](#recommended-models)
10. [Performance Optimization](#performance-optimization)

## What is LM Studio?

LM Studio is a desktop application that allows you to run large language models (LLMs) locally on your computer. It provides:

- 🖥️ User-friendly GUI for model management
- 🔌 OpenAI-compatible API server
- 🚀 GPU acceleration support (CUDA, Metal)
- 📦 Easy model downloading from HuggingFace
- ⚡ Optimized inference engine

## Prerequisites

### System Requirements

**Minimum:**
- 8 GB RAM (16 GB recommended)
- 10 GB free disk space
- macOS, Windows, or Linux

**For GPU Acceleration:**
- NVIDIA GPU with 6+ GB VRAM (CUDA)
- Apple Silicon Mac (M1/M2/M3+) with Metal support
- AMD GPU (ROCm support on Linux)

**Recommended for Best Performance:**
- 16+ GB RAM
- NVIDIA RTX 3060 or higher / Apple M1 Pro or higher
- 50+ GB free disk space (for multiple models)

## Installation

### Step 1: Download LM Studio

1. Visit [https://lmstudio.ai/](https://lmstudio.ai/)
2. Download the installer for your operating system:
   - **macOS**: `.dmg` file
   - **Windows**: `.exe` installer
   - **Linux**: `.AppImage` file

### Step 2: Install LM Studio

**macOS:**
```bash
# Open the .dmg file and drag LM Studio to Applications
open LMStudio-*.dmg
```

**Windows:**
```bash
# Run the installer
LMStudio-Setup.exe
```

**Linux:**
```bash
# Make the AppImage executable
chmod +x LM-Studio-*.AppImage
# Run it
./LM-Studio-*.AppImage
```

### Step 3: First Launch

1. Open LM Studio
2. Complete the initial setup wizard
3. Choose your preferred settings:
   - Enable GPU acceleration if available
   - Set model download directory
   - Configure memory limits

## Downloading Models

### Step 1: Open the Model Search

1. Click the 🔍 **"Search"** tab in LM Studio
2. You'll see a list of popular models

### Step 2: Choose a Model

**For QuietStories, we recommend:**

| Model | Size | RAM Needed | Best For |
|-------|------|------------|----------|
| **Llama 3.2 3B** | 3B | 8 GB | Fast responses, good quality |
| **Phi-3 Mini** | 3.8B | 8 GB | Balanced performance |
| **Mistral 7B** | 7B | 16 GB | Better quality, slower |
| **Llama 3.1 8B** | 8B | 16 GB | Excellent quality |
| **Gemma 2 9B** | 9B | 20 GB | Top quality |

**Popular choices in LM Studio search:**
- `meta-llama/Llama-3.2-3B-Instruct`
- `microsoft/Phi-3-mini-4k-instruct`
- `mistralai/Mistral-7B-Instruct-v0.3`

### Step 3: Download the Model

1. Search for your chosen model (e.g., "llama 3.2 3b")
2. Click on the model
3. Select quantization level:
   - **Q4_K_M** - Good balance (recommended)
   - **Q5_K_M** - Better quality, more VRAM
   - **Q8_0** - Highest quality, most VRAM
4. Click **"Download"**
5. Wait for download to complete (this may take several minutes)

### Understanding Quantization

- **Q4** = 4-bit quantization (smaller, faster, slightly lower quality)
- **Q5** = 5-bit quantization (balanced)
- **Q8** = 8-bit quantization (larger, slower, better quality)
- **K_M** = Medium quantization method (good default)

## Starting the Server

### Step 1: Load a Model

1. Click the 💬 **"Chat"** tab in LM Studio
2. Click **"Select a model to load"** at the top
3. Choose your downloaded model from the list
4. Wait for the model to load (you'll see GPU/CPU allocation info)

### Step 2: Start the Local Server

1. Click the 🔌 **"Local Server"** tab (or ⚡ icon)
2. Click **"Start Server"**
3. Default settings should be:
   - **Port**: `1234`
   - **Enable CORS**: ✅ (important!)
   - **API Key**: Not required (leave empty)

### Step 3: Verify Server is Running

You should see:
```
Server running on http://localhost:1234
Model loaded: llama-3.2-3b-instruct
```

**Test the server:**
```bash
curl http://localhost:1234/v1/models
```

You should get a JSON response listing your model.

### Step 4: Configure Server Settings (Optional)

Click **⚙️ "Server Settings"** to adjust:

- **Context Length**: 4096 (default) or higher for longer conversations
- **GPU Layers**: Auto or manual (more = faster but uses more VRAM)
- **Temperature**: 0.7 (default for balanced creativity)
- **Max Tokens**: 2048 (maximum response length)

**Recommended for QuietStories:**
```
Context Length: 4096
Temperature: 0.7-0.8
Max Tokens: 2048
GPU Layers: Auto (or max if you have enough VRAM)
```

## Configuring QuietStories

### Step 1: Set Environment Variables

Create or edit your `.env` file in the QuietStories root directory:

```bash
# LM Studio Configuration
MODEL_PROVIDER=lmstudio
LMSTUDIO_API_BASE=http://localhost:1234/v1
OPENAI_API_BASE=http://localhost:1234/v1
MODEL_NAME=llama-3.2-3b-instruct

# LM Studio doesn't require an API key, but you can set a dummy value
OPENAI_API_KEY=lm-studio

# Optional: Use local embeddings with LM Studio (see LOCAL_EMBEDDINGS.md)
EMBEDDING_PROVIDER=lmstudio
EMBEDDING_MODEL_NAME=local-embedding-model
EMBEDDING_API_BASE=http://localhost:1234/v1

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database Configuration
DATABASE_PATH=data/quietstories.db

# Monte Carlo Configuration
MONTE_CARLO_TURNS=100
NEGATIVITY_MIN_FAIL_RATE=0.25
```

### Step 2: Docker Configuration

If you're running QuietStories in Docker, you need to use `host.docker.internal` instead of `localhost` to connect to LM Studio running on your host machine:

```bash
# For Docker deployments (the docker-compose.yml sets these by default)
LMSTUDIO_API_BASE=http://host.docker.internal:1234/v1
OPENAI_API_BASE=http://host.docker.internal:1234/v1
EMBEDDING_API_BASE=http://host.docker.internal:1234/v1
```

**Note**: The provided `docker-compose.yml` already includes these settings, so you typically don't need to set them manually when using Docker Compose.

### Step 3: Custom Port Configuration

If you changed LM Studio's default port (1234) to something else:

```bash
# If LM Studio is running on port 5101 instead (non-Docker)
LMSTUDIO_API_BASE=http://localhost:5101/v1
OPENAI_API_BASE=http://localhost:5101/v1

# If LM Studio is running on port 5101 instead (Docker)
LMSTUDIO_API_BASE=http://host.docker.internal:5101/v1
OPENAI_API_BASE=http://host.docker.internal:5101/v1
```

### Step 4: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Optional: Install embedding dependencies for semantic search
pip install chromadb langchain-chroma langchain-community
```

### Step 5: Start QuietStories

```bash
# Start the backend
python -m uvicorn backend.main:app --reload

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

## Testing the Connection

### Method 1: Using Python Script

Create a test file `test_lmstudio_connection.py`:

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Test LM Studio connection
api_base = os.getenv("LMSTUDIO_API_BASE", "http://localhost:1234/v1")

print(f"Testing connection to {api_base}")

# Test 1: Check if server is running
try:
    response = requests.get(f"{api_base}/models")
    print("✓ Server is running")
    print(f"  Available models: {response.json()}")
except Exception as e:
    print(f"✗ Server not responding: {e}")
    exit(1)

# Test 2: Try a simple chat completion
try:
    response = requests.post(
        f"{api_base}/chat/completions",
        json={
            "model": "local-model",
            "messages": [{"role": "user", "content": "Say hello!"}],
            "max_tokens": 50
        }
    )
    result = response.json()
    print("✓ Chat completion working")
    print(f"  Response: {result['choices'][0]['message']['content']}")
except Exception as e:
    print(f"✗ Chat completion failed: {e}")
    exit(1)

print("\n✓ All tests passed! LM Studio is ready to use.")
```

Run it:
```bash
python test_lmstudio_connection.py
```

### Method 2: Using curl

```bash
# Test 1: Check models endpoint
curl http://localhost:1234/v1/models

# Test 2: Try chat completion
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

### Method 3: Via QuietStories Health Check

```bash
# Start QuietStories backend
python -m uvicorn backend.main:app --reload

# In another terminal, check health
curl http://localhost:8000/health
```

## Troubleshooting

### Issue: "Connection refused" or "Server not responding"

**Cause**: LM Studio server is not running or using different port.

**Solutions:**
1. Check if LM Studio Local Server is started (green indicator)
2. Verify the port in LM Studio matches your `.env` file
3. Check firewall settings aren't blocking localhost connections

```bash
# Check if port 1234 is in use
lsof -i :1234  # macOS/Linux
netstat -ano | findstr :1234  # Windows
```

### Issue: "Model not loaded"

**Cause**: No model loaded in LM Studio chat interface.

**Solutions:**
1. Go to LM Studio Chat tab
2. Click "Select a model to load"
3. Choose a downloaded model
4. Wait for loading to complete
5. Then start the Local Server

### Issue: Slow responses or timeouts

**Cause**: Model too large for your hardware or insufficient GPU usage.

**Solutions:**

1. **Use a smaller model:**
   - Switch from 7B to 3B model
   - Use higher quantization (Q4 instead of Q8)

2. **Optimize GPU usage:**
   - In LM Studio Server Settings, increase "GPU Layers"
   - Close other GPU-heavy applications
   - Monitor VRAM usage in LM Studio

3. **Increase timeout in QuietStories:**
   ```python
   # In backend/providers/lmstudio.py, increase timeout if needed
   ```

### Issue: "Out of memory" errors

**Cause**: Model too large for available RAM/VRAM.

**Solutions:**
1. Use smaller model (3B instead of 7B)
2. Use higher quantization (Q4_K_M instead of Q5_K_M)
3. Reduce context length in LM Studio settings
4. Close other applications to free up memory
5. Reduce "GPU Layers" to offload some work to CPU

### Issue: Embeddings not working

**Cause**: LM Studio may not have embedding model loaded.

**Solutions:**

1. **Use Ollama for embeddings instead:**
   ```bash
   # Install Ollama
   # Pull embedding model
   ollama pull nomic-embed-text

   # Update .env
   EMBEDDING_PROVIDER=ollama
   EMBEDDING_API_BASE=http://localhost:11434
   EMBEDDING_MODEL_NAME=nomic-embed-text
   ```

2. **Or disable embeddings:**
   ```bash
   EMBEDDING_PROVIDER=none
   ```

See [LOCAL_EMBEDDINGS.md](./LOCAL_EMBEDDINGS.md) for detailed embedding setup.

### Issue: CORS errors in browser

**Cause**: CORS not enabled in LM Studio.

**Solution:**
1. Go to LM Studio Local Server tab
2. Check **"Enable CORS"** checkbox
3. Restart the server

### Issue: Wrong model name errors

**Cause**: Model name in config doesn't match loaded model.

**Solution:**
The model name in `.env` doesn't need to match exactly. LM Studio uses "local-model" as a default. You can use any name:

```bash
MODEL_NAME=local-model
# or
MODEL_NAME=llama-3.2-3b-instruct
# or
MODEL_NAME=my-awesome-model
```

## Recommended Models

### Best for QuietStories

#### 1. Llama 3.2 3B Instruct (Recommended for 8GB RAM)
```
Model: meta-llama/Llama-3.2-3B-Instruct
Quantization: Q4_K_M
Size: ~2.3 GB
RAM: 6-8 GB
Quality: ⭐⭐⭐⭐
Speed: ⭐⭐⭐⭐⭐
```
**Best for:** Fast responses, good story generation, works on most hardware

#### 2. Mistral 7B Instruct (Recommended for 16GB RAM)
```
Model: mistralai/Mistral-7B-Instruct-v0.3
Quantization: Q4_K_M
Size: ~4.4 GB
RAM: 12-16 GB
Quality: ⭐⭐⭐⭐⭐
Speed: ⭐⭐⭐⭐
```
**Best for:** High-quality narratives, complex storylines, good reasoning

#### 3. Phi-3 Mini (Recommended for low-end hardware)
```
Model: microsoft/Phi-3-mini-4k-instruct
Quantization: Q4_K_M
Size: ~2.4 GB
RAM: 6-8 GB
Quality: ⭐⭐⭐⭐
Speed: ⭐⭐⭐⭐⭐
```
**Best for:** Very fast responses, decent quality, minimal hardware requirements

#### 4. Llama 3.1 8B (Recommended for best quality)
```
Model: meta-llama/Llama-3.1-8B-Instruct
Quantization: Q5_K_M
Size: ~5.8 GB
RAM: 16-20 GB
Quality: ⭐⭐⭐⭐⭐
Speed: ⭐⭐⭐
```
**Best for:** Highest quality stories, complex character interactions, nuanced dialogue

### Quantization Guide

| Quantization | File Size | Quality | Speed | Recommended For |
|--------------|-----------|---------|-------|-----------------|
| Q2_K | Smallest | ⭐⭐ | ⭐⭐⭐⭐⭐ | Testing only |
| Q3_K_M | Small | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Low-end hardware |
| **Q4_K_M** | **Medium** | **⭐⭐⭐⭐** | **⭐⭐⭐⭐** | **Recommended** |
| Q5_K_M | Large | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Good hardware |
| Q8_0 | Largest | ⭐⭐⭐⭐⭐ | ⭐⭐ | Best hardware |

## Performance Optimization

### GPU Acceleration

**NVIDIA (CUDA):**
1. Install CUDA toolkit from NVIDIA
2. LM Studio will auto-detect and use GPU
3. Monitor GPU usage in LM Studio or `nvidia-smi`

**Apple Silicon (Metal):**
1. Automatically enabled on M1/M2/M3 Macs
2. No additional setup needed
3. Check GPU usage in Activity Monitor

**AMD (ROCm - Linux only):**
1. Install ROCm drivers
2. May require manual configuration
3. Check LM Studio documentation

### Optimize Context Length

Lower context = faster responses:

```
Context Length: 2048 (fast)
Context Length: 4096 (balanced) ← recommended
Context Length: 8192 (slow but handles longer stories)
```

### Batch Processing

For better throughput:
1. In LM Studio settings, enable batch processing
2. Set batch size based on VRAM (32-128)

### Memory Management

**If running out of memory:**
1. Close browser tabs
2. Close other applications
3. Reduce GPU layers
4. Use smaller model
5. Use higher quantization (Q4 instead of Q5)

### Temperature Settings

For story generation:
```bash
# More creative, varied responses
Temperature: 0.8-1.0

# Balanced (recommended)
Temperature: 0.7

# More consistent, predictable
Temperature: 0.5-0.6
```

## Complete Setup Example

Here's a complete example for a 16GB RAM system:

### Non-Docker Setup

### 1. Download and Install LM Studio
```bash
# Download from lmstudio.ai
# Install and launch
```

### 2. Download Model
```
Search: "llama 3.2 3b"
Select: meta-llama/Llama-3.2-3B-Instruct
Quantization: Q4_K_M
Click: Download
```

### 3. Load Model and Start Server
```
1. Go to Chat tab
2. Select model: llama-3.2-3b-instruct-q4_k_m
3. Wait for model to load
4. Go to Local Server tab
5. Click "Start Server"
6. Verify: http://localhost:1234
```

### 4. Configure QuietStories
```bash
# Create .env file
cat > .env << EOF
MODEL_PROVIDER=lmstudio
LMSTUDIO_API_BASE=http://localhost:1234/v1
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
MODEL_NAME=llama-3.2-3b-instruct

HOST=0.0.0.0
PORT=8000
DEBUG=false
EOF
```

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

### 6. Test Connection
```bash
curl http://localhost:1234/v1/models
```

### 7. Start QuietStories
```bash
# Terminal 1: Backend
python -m uvicorn backend.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 8. Open Browser
```
Navigate to: http://localhost:5173
Start creating stories!
```

### Docker Setup

When running QuietStories in Docker, the configuration is even simpler:

### 1. Install and Start LM Studio on Host Machine
```bash
# Download from lmstudio.ai
# Install and launch
# Download a model (e.g., Llama 3.2 3B)
# Load the model and start the Local Server on port 1234
```

### 2. Start QuietStories with Docker Compose
```bash
# No .env file needed - docker-compose.yml handles the configuration
docker-compose --profile full up

# Or start just the backend
docker-compose --profile api-only up
```

The `docker-compose.yml` is already configured to use `host.docker.internal:1234` to connect to LM Studio running on your host machine. No additional configuration needed!

### 3. Access the Application
```
API: http://localhost:8000
Frontend: http://localhost:5173 (if using --profile full)
```

**Note**: On Linux, `host.docker.internal` is automatically mapped to the host gateway in the docker-compose.yml file, so it works across all platforms (Windows, macOS, and Linux).

## Next Steps

- 📖 Read [LOCAL_EMBEDDINGS.md](./LOCAL_EMBEDDINGS.md) for semantic search setup
- 🎮 Try different models to find your preferred quality/speed balance
- ⚙️ Experiment with temperature and context length settings
- 📊 Monitor resource usage to optimize performance

## Useful Resources

- **LM Studio**: https://lmstudio.ai/
- **LM Studio Discord**: https://discord.gg/lmstudio
- **Model Search**: https://huggingface.co/models
- **Quantization Guide**: https://github.com/ggerganov/llama.cpp/discussions/2094

## Support

If you encounter issues:

1. Check LM Studio logs (View → Developer Tools → Console)
2. Check QuietStories logs in `logs/` directory
3. Verify environment variables: `cat .env`
4. Test connection: `curl http://localhost:1234/v1/models`
5. Join our community or create a GitHub issue

---

**Happy storytelling with local LLMs! 🎭✨**
