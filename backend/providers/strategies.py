"""
Strategy pattern implementations for different LLM provider types.

Provides specialized handling for different model families:
- OpenAIGPT5Strategy: GPT-5 models using Responses API
- OpenAIGPT4oStrategy: GPT-4o models using Chat Completions
- OpenAICompatibleStrategy: LM Studio/Ollama with OpenAI-compatible API
"""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from backend.utils.logger import get_logger

from .base import ProviderResponse
from .capabilities import ModelCapabilities

logger = get_logger(__name__)


class ProviderStrategy(ABC):
    """Abstract base class for provider strategies."""

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model_name: str,
        capabilities: ModelCapabilities,
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.model_name = model_name
        self.capabilities = capabilities
        self.llm: Any = None

    @abstractmethod
    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to the provider."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from LLM response with robust handling.

        Handles:
        - Markdown code blocks
        - Extra text before/after JSON
        - Common formatting issues

        Args:
            content: Raw LLM response

        Returns:
            Cleaned JSON string
        """
        content = content.strip()

        # Remove markdown code blocks
        if "```" in content:
            # Extract content between code fences
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
            if match:
                content = match.group(1)
                logger.debug("Extracted JSON from markdown code block")
            else:
                # Fallback: remove all lines with ```
                lines = [
                    line
                    for line in content.split("\n")
                    if not line.strip().startswith("```")
                ]
                content = "\n".join(lines)
                logger.debug("Removed markdown code fence lines")

        # Extract JSON object
        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx]
            logger.debug(f"Extracted JSON substring (length {len(content)})")

        return content


class OpenAIGPT5Strategy(ProviderStrategy):
    """
    Strategy for GPT-5 models using Responses API.

    GPT-5 models have special characteristics:
    - Do not support temperature parameter (fixed at 1.0)
    - May produce JSON responses with formatting issues
    - Require robust JSON extraction
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model_name: str,
        capabilities: ModelCapabilities,
    ):
        super().__init__(api_base, api_key, model_name, capabilities)

        # Initialize ChatOpenAI without temperature for GPT-5
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=api_base,
            api_key=api_key,  # type: ignore
        )

    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to GPT-5 model."""
        try:
            # Configure LLM with parameters (but not temperature)
            llm = self.llm

            # GPT-5 doesn't support temperature parameter
            if "temperature" in kwargs:
                logger.warning(
                    f"GPT-5 model {self.model_name} does not support temperature parameter, ignoring"
                )

            if "max_tokens" in kwargs:
                llm = llm.bind(max_tokens=kwargs["max_tokens"])

            # Handle tools if provided
            if tools:
                llm_with_tools = llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)

            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, messages, tools, **kwargs)

            # Extract content
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Apply robust JSON extraction if needed
            if json_schema or self.capabilities.requires_special_json_parsing:
                try:
                    # Try to parse as-is first
                    json.loads(content)
                except json.JSONDecodeError:
                    logger.info("Applying robust JSON extraction for GPT-5 response")
                    content = self._extract_json_from_response(content)

            # Extract tool calls
            tool_calls = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = [
                    {
                        "id": tc.get("id"),
                        "type": tc.get("type"),
                        "function": {
                            "name": tc.get("name"),
                            "arguments": tc.get("args"),
                        },
                    }
                    for tc in response.tool_calls
                ]

            return ProviderResponse(
                content=content,
                usage=getattr(response, "usage_metadata", None),
                model=self.model_name,
                tool_calls=tool_calls,
            )

        except Exception as e:
            raise Exception(f"GPT-5 API error: {e}")

    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses."""
        if tools:
            return llm.bind_tools(tools)
        return llm

    async def health_check(self) -> bool:
        """Check if GPT-5 API is accessible."""
        try:
            from langchain_core.messages import HumanMessage

            test_message = HumanMessage(content="Hello")
            await self.llm.ainvoke([test_message])
            return True
        except Exception:
            return False


class OpenAIGPT4oStrategy(ProviderStrategy):
    """
    Strategy for GPT-4o and earlier models using Chat Completions API.

    These models support all standard OpenAI API features:
    - Temperature control
    - Tool calling
    - Structured output
    - Streaming
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model_name: str,
        capabilities: ModelCapabilities,
    ):
        super().__init__(api_base, api_key, model_name, capabilities)

        # Initialize ChatOpenAI with default temperature
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=api_base,
            api_key=api_key,  # type: ignore
            temperature=0.7,
        )

    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to GPT-4o model."""
        try:
            # Configure LLM with parameters
            llm = self.llm

            if "temperature" in kwargs:
                llm = llm.bind(temperature=kwargs["temperature"])

            if "max_tokens" in kwargs:
                llm = llm.bind(max_tokens=kwargs["max_tokens"])

            # Handle tools if provided
            if tools:
                llm_with_tools = llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)

            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, messages, tools, **kwargs)

            # Extract content and tool calls
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            tool_calls = None

            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = [
                    {
                        "id": tc.get("id"),
                        "type": tc.get("type"),
                        "function": {
                            "name": tc.get("name"),
                            "arguments": tc.get("args"),
                        },
                    }
                    for tc in response.tool_calls
                ]

            return ProviderResponse(
                content=content,
                usage=getattr(response, "usage_metadata", None),
                model=self.model_name,
                tool_calls=tool_calls,
            )

        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")

    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses."""
        if tools:
            return llm.bind_tools(tools)
        return llm

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            from langchain_core.messages import HumanMessage

            test_message = HumanMessage(content="Hello")
            await self.llm.ainvoke([test_message])
            return True
        except Exception:
            return False


class OpenAICompatibleStrategy(ProviderStrategy):
    """
    Strategy for OpenAI-compatible APIs (LM Studio, Ollama, etc.).

    These providers implement the OpenAI API format but may have limitations:
    - Tool calling support varies
    - Structured output support varies
    - May require robust JSON extraction
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model_name: str,
        capabilities: ModelCapabilities,
    ):
        super().__init__(api_base, api_key, model_name, capabilities)

        # Initialize ChatOpenAI with default settings
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=api_base,
            api_key=api_key or "not-needed",  # type: ignore
            temperature=0.7,
            max_tokens=capabilities.default_max_tokens,
        )

    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to OpenAI-compatible API."""
        try:
            # Configure LLM with parameters
            llm = self.llm

            if "temperature" in kwargs and self.capabilities.supports_temperature:
                llm = llm.bind(temperature=kwargs["temperature"])

            if "max_tokens" in kwargs:
                llm = llm.bind(max_tokens=kwargs["max_tokens"])

            # Handle tools if supported
            if tools and self.capabilities.supports_tools:
                try:
                    llm_with_tools = llm.bind_tools(tools)
                    response = await llm_with_tools.ainvoke(messages)
                except Exception as e:
                    logger.warning(f"Tool binding not supported: {e}")
                    response = await llm.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)

            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, messages, tools, **kwargs)

            # Extract content
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Apply robust JSON extraction if needed
            if json_schema or self.capabilities.requires_special_json_parsing:
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    logger.info("Applying robust JSON extraction")
                    content = self._extract_json_from_response(content)

            # Extract tool calls if available
            tool_calls = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                try:
                    tool_calls = [
                        {
                            "id": tc.get("id"),
                            "type": tc.get("type"),
                            "function": {
                                "name": tc.get("name"),
                                "arguments": tc.get("args"),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                except Exception as e:
                    logger.warning(f"Failed to extract tool calls: {e}")

            # Get usage metadata if available, otherwise estimate
            usage = getattr(response, "usage_metadata", None)
            if not usage:
                # Estimate tokens for local models
                usage = {
                    "prompt_tokens": sum(len(str(m.content).split()) for m in messages),
                    "completion_tokens": len(content.split()),
                    "total_tokens": sum(len(str(m.content).split()) for m in messages)
                    + len(content.split()),
                }

            return ProviderResponse(
                content=content,
                usage=usage,
                model=self.model_name,
                tool_calls=tool_calls,
            )

        except Exception as e:
            raise Exception(f"OpenAI-compatible API error: {e}")

    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses."""
        if tools and self.capabilities.supports_tools:
            try:
                return llm.bind_tools(tools)
            except Exception:
                pass
        return llm

    async def health_check(self) -> bool:
        """Check if OpenAI-compatible API is accessible."""
        try:
            from langchain_core.messages import HumanMessage

            test_message = HumanMessage(content="Hello")
            await self.llm.ainvoke([test_message])
            return True
        except Exception:
            return False
