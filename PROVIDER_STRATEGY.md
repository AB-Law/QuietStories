# Provider Strategy Pattern

## Overview

The QuietStories backend uses a **Strategy Pattern** to support multiple LLM model families with different capabilities and API requirements. This enables seamless switching between GPT-5, GPT-4o, GPT-4, and OpenAI-compatible models (like LM Studio and Ollama).

## Architecture

### Core Components

1. **`capabilities.py`**: Model family detection and capability mapping
2. **`strategies.py`**: Strategy pattern implementations for different model families
3. **`openai.py`**: Updated OpenAIProvider with automatic strategy routing
4. **`factory.py`**: Provider factory that creates the appropriate provider

### Model Family Detection

The system automatically detects model families based on model name prefixes:

- **GPT-5**: Models starting with `gpt-5` (e.g., `gpt-5-nano`, `gpt-5-mini`)
- **GPT-4o**: Models starting with `gpt-4o` (e.g., `gpt-4o`, `gpt-4o-mini`)
- **GPT-4**: Models starting with `gpt-4` (e.g., `gpt-4`, `gpt-4-turbo`)
- **GPT-3.5**: Models starting with `gpt-3.5`
- **OpenAI-compatible**: Non-GPT models (e.g., `llama-3`, `mistral`)

## Model Capabilities

Each model family has different capabilities:

### GPT-5 Family (Responses API)
- ❌ Temperature control (fixed at 1.0)
- ✅ Tool calling
- ✅ Structured output
- ✅ Streaming
- ⚠️ Requires special JSON parsing (may produce malformed JSON)

### GPT-4o/GPT-4 Family (Chat Completions API)
- ✅ Temperature control
- ✅ Tool calling
- ✅ Structured output
- ✅ Streaming
- ✅ Standard JSON parsing

### OpenAI-Compatible (LM Studio, Ollama)
- ✅ Temperature control
- ⚠️ Tool calling (varies by model)
- ⚠️ Structured output (varies by model)
- ✅ Streaming
- ⚠️ Requires robust JSON parsing

## Strategy Pattern Implementation

### Base Strategy

```python
class ProviderStrategy(ABC):
    """Abstract base class for provider strategies."""
    
    @abstractmethod
    async def chat(self, messages, tools, json_schema, stream, **kwargs):
        """Send chat request to the provider."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass
```

### Concrete Strategies

1. **`OpenAIGPT5Strategy`**: Handles GPT-5 specific requirements
   - Removes temperature parameter
   - Applies robust JSON extraction
   - Uses Responses API

2. **`OpenAIGPT4oStrategy`**: Handles GPT-4o and earlier models
   - Supports full temperature control
   - Uses Chat Completions API
   - Standard JSON handling

3. **`OpenAICompatibleStrategy`**: Handles LM Studio/Ollama
   - Conservative capability assumptions
   - Graceful degradation for unsupported features
   - Robust JSON extraction

## Automatic Routing

The `OpenAIProvider` automatically selects the appropriate strategy:

```python
provider = OpenAIProvider(
    api_base="https://api.openai.com/v1",
    api_key="your-key",
    model_name="gpt-5-nano"  # Automatically uses OpenAIGPT5Strategy
)
```

## JSON Extraction

All strategies include robust JSON extraction to handle:
- Markdown code blocks (```json ... ```)
- Extra text before/after JSON
- Common formatting issues from LLMs

Example:
```python
# Input
content = '```json\n{"key": "value"}\n```'

# After extraction
result = '{"key": "value"}'
```

## Usage Examples

### Using GPT-5 Model
```python
from backend.providers import create_provider
from backend.config import settings

# Set in .env or environment
settings.model_provider = "openai"
settings.model_name = "gpt-5-nano"

provider = create_provider()
# Automatically uses OpenAIGPT5Strategy
```

### Using GPT-4o Model
```python
settings.model_provider = "openai"
settings.model_name = "gpt-4o"

provider = create_provider()
# Automatically uses OpenAIGPT4oStrategy
```

### Using LM Studio
```python
settings.model_provider = "lmstudio"
settings.model_name = "llama-3"
settings.lmstudio_api_base = "http://localhost:1234/v1"

provider = create_provider()
# Uses LMStudioProvider (wraps OpenAI-compatible API)
```

## Testing

The strategy pattern is thoroughly tested with 26 comprehensive tests covering:

- Model family detection
- Capability mapping
- Strategy selection
- JSON extraction
- Temperature handling
- Compatibility with BaseProvider interface

Run tests:
```bash
pytest backend/tests/test_provider_strategies.py -v
```

## Benefits

1. **Extensibility**: Easy to add new model families
2. **Maintainability**: Each strategy handles its specific concerns
3. **Robustness**: Automatic fallback and error handling
4. **Flexibility**: Seamless switching between providers
5. **Type Safety**: Full mypy type checking support

## Future Enhancements

Potential additions to the strategy pattern:

- [ ] Support for Anthropic Claude models
- [ ] Support for Google Gemini models
- [ ] Custom retry strategies per model family
- [ ] Model-specific prompt optimization
- [ ] Cost tracking per model family
