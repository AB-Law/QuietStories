# Local Embeddings for Semantic Memory Search

## Overview

QuietStories now supports **fully local embedding models** for semantic memory search, eliminating the need for OpenAI API access when using local LLMs like Ollama or LM Studio.

## Why Local Embeddings?

When using local LLMs (Ollama, LM Studio), you shouldn't need to rely on OpenAI's API for embeddings. Local embeddings provide:

- ✅ **Complete privacy** - All data stays on your machine
- ✅ **No API costs** - Free embedding generation
- ✅ **Offline capability** - Works without internet
- ✅ **Consistency** - Single local provider for LLM + embeddings

## Configuration

### Environment Variables

```bash
# Embedding Provider (auto-detects from model_provider if not set)
EMBEDDING_PROVIDER=ollama  # Options: openai, ollama, lmstudio, none

# Embedding Model Name
EMBEDDING_MODEL_NAME=nomic-embed-text  # For Ollama
# EMBEDDING_MODEL_NAME=text-embedding-3-small  # For OpenAI
# EMBEDDING_MODEL_NAME=local-embedding-model  # For LM Studio

# Embedding API Base (optional, defaults to model provider's base URL)
EMBEDDING_API_BASE=http://localhost:11434  # For Ollama
```

## Provider Setup

### 1. Ollama Embeddings (Recommended for Local)

**Install Ollama embedding model:**
```bash
ollama pull nomic-embed-text
```

**Configure:**
```bash
MODEL_PROVIDER=ollama
OPENAI_API_BASE=http://localhost:11434
MODEL_NAME=llama3.2:3b

# Embeddings (auto-detected)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_NAME=nomic-embed-text
```

**Available Ollama Embedding Models:**
- `nomic-embed-text` - Excellent general-purpose embeddings (137M params)
- `mxbai-embed-large` - High-quality embeddings (335M params)
- `all-minilm` - Fast, compact embeddings (22M params)

### 2. LM Studio Embeddings

LM Studio supports OpenAI-compatible embedding endpoints.

**Configure:**
```bash
MODEL_PROVIDER=lmstudio
OPENAI_API_BASE=http://localhost:5101/v1
MODEL_NAME=your-chat-model

# Embeddings (uses same LM Studio instance)
EMBEDDING_PROVIDER=lmstudio
EMBEDDING_MODEL_NAME=local-embedding-model
```

### 3. OpenAI Embeddings (Cloud)

**Configure:**
```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
MODEL_NAME=gpt-4

# Embeddings (auto-detected)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-small
```

### 4. Disable Semantic Search

If you don't want semantic memory search:

```bash
EMBEDDING_PROVIDER=none
```

Memories will still work but won't support semantic similarity queries.

## Auto-Detection

If `EMBEDDING_PROVIDER` is not set, the system automatically uses the same provider as `MODEL_PROVIDER`:

- `MODEL_PROVIDER=ollama` → Uses Ollama embeddings
- `MODEL_PROVIDER=lmstudio` → Uses LM Studio embeddings
- `MODEL_PROVIDER=openai` → Uses OpenAI embeddings

## Example Configurations

### Fully Local Setup (No API Keys)

```bash
# .env
MODEL_PROVIDER=ollama
OPENAI_API_BASE=http://localhost:11434
MODEL_NAME=llama3.2:3b
# EMBEDDING_PROVIDER will auto-detect to 'ollama'
# EMBEDDING_MODEL_NAME will default to 'nomic-embed-text'
```

### Hybrid Setup (Local LLM + OpenAI Embeddings)

```bash
# .env
MODEL_PROVIDER=ollama
OPENAI_API_BASE=http://localhost:11434
MODEL_NAME=llama3.2:3b

# Use OpenAI for better embeddings
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL_NAME=text-embedding-3-small
```

## Testing

The system automatically tests the embedding provider on startup. Check logs for:

```
✓ Initialized Ollama embeddings: nomic-embed-text at http://localhost:11434
✓ Embedding provider test passed (dimension: 768)
```

## Troubleshooting

### Embeddings Not Working

1. **Check if provider is running:**
   ```bash
   # Ollama
   curl http://localhost:11434/api/version

   # LM Studio
   curl http://localhost:5101/v1/models
   ```

2. **Verify model is installed:**
   ```bash
   # Ollama
   ollama list | grep nomic-embed-text
   ```

3. **Check logs:**
   ```
   [2025-10-15 10:30:45] INFO: Creating embedding provider: ollama
   [2025-10-15 10:30:45] INFO: ✓ Initialized Ollama embeddings: nomic-embed-text
   ```

### Performance Issues

- **Ollama**: Use `nomic-embed-text` for best balance of speed/quality
- **Large models**: Consider `all-minilm` for faster embeddings with acceptable quality
- **Memory**: Embeddings use ~200MB RAM for nomic-embed-text

## Benefits of Semantic Search

With embeddings enabled, the memory system can:

- Find relevant memories by meaning, not just keywords
- Understand context and relationships
- Retrieve memories across paraphrasing
- Support complex queries

Example:
```
Query: "What does Marcus think about the artifact?"
Matches: "Marcus seems suspicious of the ancient relic"
         "The guardian expressed concerns about the object"
```

## Architecture

```
SemanticMemorySearch
├── create_embedding_provider()
│   ├── OpenAIEmbeddings (cloud)
│   ├── OllamaEmbeddings (local)
│   └── LMStudioEmbeddings (local, OpenAI-compatible)
├── ChromaDB (vector database)
└── LangChain (integration layer)
```

## Migration from Previous Version

Previously, semantic search **required** OpenAI API key. Now:

**Before:**
```bash
MODEL_PROVIDER=ollama
OPENAI_API_KEY=sk-...  # Required for embeddings even with local LLM!
```

**After:**
```bash
MODEL_PROVIDER=ollama
# No API key needed - fully local!
```

## Future Enhancements

- [ ] HuggingFace local embeddings support
- [ ] Embedding model benchmarking tool
- [ ] Custom embedding dimension configuration
- [ ] Multi-language embedding models
- [ ] Embedding cache for frequently queried memories
