"""
OpenAI provider implementation using LangChain with strategy pattern
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from backend.utils.logger import get_logger

from .base import BaseProvider, ProviderResponse
from .capabilities import (
    APIFamily,
    get_api_family,
    get_model_capabilities,
    is_gpt4o_model,
    is_gpt5_model,
)
from .strategies import (
    OpenAICompatibleStrategy,
    OpenAIGPT4oStrategy,
    OpenAIGPT5Strategy,
    ProviderStrategy,
)

logger = get_logger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider using LangChain with strategy pattern"""

    def __init__(self, api_base: str, api_key: str, model_name: str):
        super().__init__(api_base, api_key, model_name)

        # Get model capabilities
        self.capabilities = get_model_capabilities(model_name)
        self.api_family = get_api_family(model_name)

        # Select appropriate strategy based on model family
        self.strategy: ProviderStrategy = self._create_strategy()

        # Set llm from strategy for compatibility
        self.llm = self.strategy.llm

        logger.info(
            f"Initialized OpenAI provider with strategy for {model_name} (API family: {self.api_family})"
        )

    def _create_strategy(self) -> ProviderStrategy:
        """Create appropriate strategy based on model capabilities."""
        if is_gpt5_model(self.model_name):
            logger.info(f"Using GPT-5 strategy for {self.model_name}")
            return OpenAIGPT5Strategy(
                self.api_base, self.api_key, self.model_name, self.capabilities
            )
        elif is_gpt4o_model(self.model_name) or self.model_name.startswith("gpt-"):
            logger.info(f"Using GPT-4o/Chat Completions strategy for {self.model_name}")
            return OpenAIGPT4oStrategy(
                self.api_base, self.api_key, self.model_name, self.capabilities
            )
        else:
            logger.info(f"Using OpenAI-compatible strategy for {self.model_name}")
            return OpenAICompatibleStrategy(
                self.api_base, self.api_key, self.model_name, self.capabilities
            )

    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to OpenAI API using strategy pattern"""

        # Log the LLM call
        call_id = self._log_llm_call(messages, tools, **kwargs)
        start_time = time.time()

        try:
            # Delegate to strategy
            response = await self.strategy.chat(
                messages, tools, json_schema, stream, **kwargs
            )

            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log response if not streaming
            if not stream and isinstance(response, ProviderResponse):
                # Create a mock response object for logging
                class MockResponse:
                    def __init__(self, pr: ProviderResponse):
                        self.content = pr.content
                        self.usage_metadata = pr.usage
                        self.tool_calls = pr.tool_calls

                mock_response = MockResponse(response)
                self._log_llm_response(call_id, mock_response, duration_ms)

            return response

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_llm_response(call_id, None, duration_ms, error=e)
            raise Exception(f"OpenAI API error: {e}")

    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses - delegates to strategy"""
        return await self.strategy._handle_streaming_response(
            llm, messages, tools, **kwargs
        )

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible - delegates to strategy"""
        return await self.strategy.health_check()
