"""
Tests for provider strategy pattern and capabilities detection.
"""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from backend.providers.capabilities import (
    APIFamily,
    detect_model_family,
    get_api_family,
    get_model_capabilities,
    is_gpt4o_model,
    is_gpt5_model,
)
from backend.providers.openai import OpenAIProvider
from backend.providers.strategies import (
    OpenAICompatibleStrategy,
    OpenAIGPT4oStrategy,
    OpenAIGPT5Strategy,
)


class TestModelCapabilities:
    """Test model capabilities detection and routing."""

    def test_detect_gpt5_family(self):
        """Test GPT-5 model family detection."""
        assert detect_model_family("gpt-5-nano") == "gpt-5"
        assert detect_model_family("gpt-5-mini") == "gpt-5"
        assert detect_model_family("gpt-5-turbo") == "gpt-5"

    def test_detect_gpt4o_family(self):
        """Test GPT-4o model family detection."""
        assert detect_model_family("gpt-4o") == "gpt-4o"
        assert detect_model_family("gpt-4o-mini") == "gpt-4o"

    def test_detect_gpt4_family(self):
        """Test GPT-4 model family detection."""
        assert detect_model_family("gpt-4") == "gpt-4"
        assert detect_model_family("gpt-4-turbo") == "gpt-4"

    def test_detect_unknown_gpt_model(self):
        """Test unknown GPT model defaults to gpt-4."""
        assert detect_model_family("gpt-6") == "gpt-4"

    def test_detect_non_openai_model(self):
        """Test non-OpenAI model detection."""
        assert detect_model_family("llama-3") == "openai-compatible"
        assert detect_model_family("mistral") == "openai-compatible"

    def test_gpt5_capabilities(self):
        """Test GPT-5 model capabilities."""
        caps = get_model_capabilities("gpt-5-nano")
        assert caps.api_family == APIFamily.RESPONSES
        assert caps.supports_temperature is False
        assert caps.supports_tools is True
        assert caps.requires_special_json_parsing is True

    def test_gpt4o_capabilities(self):
        """Test GPT-4o model capabilities."""
        caps = get_model_capabilities("gpt-4o")
        assert caps.api_family == APIFamily.CHAT_COMPLETIONS
        assert caps.supports_temperature is True
        assert caps.supports_tools is True
        assert caps.requires_special_json_parsing is False

    def test_unknown_model_capabilities(self):
        """Test unknown model gets safe defaults."""
        caps = get_model_capabilities("unknown-model")
        assert caps.api_family == APIFamily.OPENAI_COMPATIBLE
        assert caps.supports_temperature is True
        assert caps.supports_tools is False
        assert caps.requires_special_json_parsing is True

    def test_is_gpt5_model(self):
        """Test GPT-5 model check."""
        assert is_gpt5_model("gpt-5-nano") is True
        assert is_gpt5_model("gpt-5-mini") is True
        assert is_gpt5_model("gpt-4o") is False

    def test_is_gpt4o_model(self):
        """Test GPT-4o model check."""
        assert is_gpt4o_model("gpt-4o") is True
        assert is_gpt4o_model("gpt-4o-mini") is True
        assert is_gpt4o_model("gpt-5-nano") is False

    def test_get_api_family(self):
        """Test API family detection."""
        assert get_api_family("gpt-5-nano") == APIFamily.RESPONSES
        assert get_api_family("gpt-4o") == APIFamily.CHAT_COMPLETIONS
        assert get_api_family("gpt-4") == APIFamily.CHAT_COMPLETIONS
        assert get_api_family("llama-3") == APIFamily.OPENAI_COMPATIBLE


class TestStrategySelection:
    """Test automatic strategy selection in OpenAIProvider."""

    def test_gpt5_strategy_selection(self):
        """Test GPT-5 models use GPT5Strategy."""
        provider = OpenAIProvider(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
        )
        assert isinstance(provider.strategy, OpenAIGPT5Strategy)
        assert provider.api_family == APIFamily.RESPONSES

    def test_gpt4o_strategy_selection(self):
        """Test GPT-4o models use GPT4oStrategy."""
        provider = OpenAIProvider(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-4o",
        )
        assert isinstance(provider.strategy, OpenAIGPT4oStrategy)
        assert provider.api_family == APIFamily.CHAT_COMPLETIONS

    def test_gpt4_strategy_selection(self):
        """Test GPT-4 models use GPT4oStrategy."""
        provider = OpenAIProvider(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-4-turbo",
        )
        assert isinstance(provider.strategy, OpenAIGPT4oStrategy)
        assert provider.api_family == APIFamily.CHAT_COMPLETIONS

    def test_generic_strategy_selection(self):
        """Test non-GPT models use OpenAICompatibleStrategy."""
        provider = OpenAIProvider(
            api_base="http://localhost:1234/v1",
            api_key="not-needed",
            model_name="llama-3",
        )
        assert isinstance(provider.strategy, OpenAICompatibleStrategy)


class TestJSONExtraction:
    """Test robust JSON extraction for GPT-5 responses."""

    def test_extract_json_from_markdown(self):
        """Test JSON extraction from markdown code blocks."""
        strategy = OpenAIGPT5Strategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
            capabilities=get_model_capabilities("gpt-5-nano"),
        )

        # Test with markdown code block
        content = '```json\n{"key": "value"}\n```'
        result = strategy._extract_json_from_response(content)
        assert result == '{"key": "value"}'

    def test_extract_json_with_extra_text(self):
        """Test JSON extraction with extra text before/after."""
        strategy = OpenAIGPT5Strategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
            capabilities=get_model_capabilities("gpt-5-nano"),
        )

        content = 'Here is the JSON:\n{"key": "value"}\nThat was the JSON.'
        result = strategy._extract_json_from_response(content)
        assert result == '{"key": "value"}'

    def test_extract_json_plain(self):
        """Test JSON extraction when already clean."""
        strategy = OpenAIGPT5Strategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
            capabilities=get_model_capabilities("gpt-5-nano"),
        )

        content = '{"key": "value"}'
        result = strategy._extract_json_from_response(content)
        assert result == '{"key": "value"}'


class TestStrategyCompatibility:
    """Test that strategies maintain compatibility with BaseProvider interface."""

    def test_gpt5_strategy_has_llm(self):
        """Test GPT-5 strategy has llm attribute."""
        strategy = OpenAIGPT5Strategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
            capabilities=get_model_capabilities("gpt-5-nano"),
        )
        assert strategy.llm is not None

    def test_gpt4o_strategy_has_llm(self):
        """Test GPT-4o strategy has llm attribute."""
        strategy = OpenAIGPT4oStrategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-4o",
            capabilities=get_model_capabilities("gpt-4o"),
        )
        assert strategy.llm is not None

    def test_compatible_strategy_has_llm(self):
        """Test OpenAI-compatible strategy has llm attribute."""
        strategy = OpenAICompatibleStrategy(
            api_base="http://localhost:1234/v1",
            api_key="not-needed",
            model_name="llama-3",
            capabilities=get_model_capabilities("llama-3"),
        )
        assert strategy.llm is not None

    def test_provider_has_llm_from_strategy(self):
        """Test that provider exposes llm from strategy."""
        provider = OpenAIProvider(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
        )
        assert provider.llm is not None
        assert provider.llm == provider.strategy.llm


class TestTemperatureHandling:
    """Test temperature parameter handling across strategies."""

    def test_gpt5_ignores_temperature(self):
        """Test GPT-5 strategy ignores temperature parameter."""
        strategy = OpenAIGPT5Strategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
            capabilities=get_model_capabilities("gpt-5-nano"),
        )
        # Verify temperature not set in initialization
        assert (
            not hasattr(strategy.llm, "temperature") or strategy.llm.temperature is None
        )

    def test_gpt4o_supports_temperature(self):
        """Test GPT-4o strategy supports temperature parameter."""
        strategy = OpenAIGPT4oStrategy(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-4o",
            capabilities=get_model_capabilities("gpt-4o"),
        )
        # Verify temperature is set in initialization
        assert hasattr(strategy.llm, "temperature")

    def test_compatible_supports_temperature(self):
        """Test OpenAI-compatible strategy supports temperature."""
        strategy = OpenAICompatibleStrategy(
            api_base="http://localhost:1234/v1",
            api_key="not-needed",
            model_name="llama-3",
            capabilities=get_model_capabilities("llama-3"),
        )
        # Verify temperature is set in initialization
        assert hasattr(strategy.llm, "temperature")


@pytest.mark.asyncio
class TestStrategyIntegration:
    """Integration tests for strategy pattern (requires mocking or actual API)."""

    async def test_provider_delegates_to_strategy(self):
        """Test that provider correctly delegates to strategy."""
        provider = OpenAIProvider(
            api_base="https://api.openai.com/v1",
            api_key="test-key",
            model_name="gpt-5-nano",
        )

        # Verify strategy is set
        assert provider.strategy is not None
        assert isinstance(provider.strategy, OpenAIGPT5Strategy)

        # Verify delegation happens (will fail without real API, but structure is correct)
        messages = [SystemMessage(content="You are a helpful assistant")]
        # Note: This would need mocking or real API key to actually test
        # For now, we just verify the structure is correct
        assert hasattr(provider, "chat")
        assert hasattr(provider.strategy, "chat")
