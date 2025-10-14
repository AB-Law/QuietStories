"""
Abstract base class for LLM providers using LangChain
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain.tools import BaseTool
from pydantic import BaseModel

from backend.utils.logger import get_logger

# from langchain.schema.output import LLMResult  # Not needed for now


logger = get_logger(__name__)


class ProviderResponse(BaseModel):
    """Response from an LLM provider"""

    content: str
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers using LangChain"""

    def __init__(self, api_base: str, api_key: str, model_name: str):
        self.api_base = api_base
        self.api_key = api_key
        self.model_name = model_name
        self.llm: Any = None  # Will be set by subclasses

    def _log_llm_call(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        **kwargs,
    ) -> str:
        """Log LLM call details and return a call ID for correlation"""
        call_id = str(uuid.uuid4())[:8]
        # Count message types and extract content
        message_counts: Dict[str, int] = {}
        total_chars: int = 0
        message_details: List[Dict[str, Any]] = []
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            message_counts[msg_type] = message_counts.get(msg_type, 0) + 1
            if hasattr(msg, "content"):
                content = str(msg.content)
                total_chars += len(content)
                message_details.append(
                    {
                        "index": i,
                        "type": msg_type,
                        "content_preview": (
                            content[:200] + "..." if len(content) > 200 else content
                        ),
                        "content_length": len(content),
                    }
                )

        # Extract tool details
        tool_details: List[Dict[str, Any]] = []
        if tools:
            for tool in tools:
                tool_details.append(
                    {
                        "name": tool.name,
                        "description": (
                            tool.description[:100] + "..."
                            if len(tool.description) > 100
                            else tool.description
                        ),
                    }
                )

        # Extract key parameters
        temperature = kwargs.get("temperature", "default")
        max_tokens = kwargs.get("max_tokens", "default")
        has_tools = len(tools) if tools else 0

        logger.info(
            f"[LLM] Call started: {self.model_name}",
            extra={
                "component": "LLM",
                "call_id": call_id,
                "model": self.model_name,
                "provider": self.__class__.__name__,
                "message_count": len(messages),
                "message_types": message_counts,
                "message_details": message_details,
                "total_input_chars": total_chars,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tool_count": has_tools,
                "tool_details": tool_details,
                "request_params": {
                    k: v for k, v in kwargs.items() if k not in ["messages", "tools"]
                },
            },
        )

        return call_id

    def _log_llm_response(
        self,
        call_id: str,
        response: Any,
        duration_ms: float,
        error: Optional[Exception] = None,
    ):
        """Log LLM response details with full content"""
        if error:
            logger.error(
                f"[LLM] Call failed: {self.model_name} ({duration_ms}ms): {str(error)}",
                extra={
                    "component": "LLM",
                    "call_id": call_id,
                    "model": self.model_name,
                    "provider": self.__class__.__name__,
                    "duration_ms": duration_ms,
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
                exc_info=True,
            )
        else:
            # Extract response details
            response_chars = 0
            response_content = ""
            tool_calls = []
            usage_info = {}

            if hasattr(response, "content"):
                response_content = str(response.content)
                response_chars = len(response_content)

            if hasattr(response, "tool_calls") and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_calls.append(
                        {
                            "id": getattr(tool_call, "id", "unknown"),
                            "name": getattr(tool_call, "name", "unknown"),
                            "args": getattr(tool_call, "args", {}),
                        }
                    )

            if hasattr(response, "usage_metadata"):
                usage_info = response.usage_metadata
            elif (
                hasattr(response, "response_metadata")
                and "token_usage" in response.response_metadata
            ):
                usage_info = response.response_metadata["token_usage"]

            logger.info(
                f"[LLM] Call completed: {self.model_name} ({duration_ms}ms)",
                extra={
                    "component": "LLM",
                    "call_id": call_id,
                    "model": self.model_name,
                    "provider": self.__class__.__name__,
                    "duration_ms": duration_ms,
                    "response_chars": response_chars,
                    "response_content": response_content,
                    "tool_calls": tool_calls,
                    "usage": usage_info,
                    "response_type": type(response).__name__,
                },
            )

    @abstractmethod
    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """
        Send a chat request to the LLM provider

        Args:
            messages: List of LangChain message objects
            tools: Optional list of LangChain tools for function calling
            json_schema: Optional JSON schema for structured output
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters

        Returns:
            ProviderResponse or streaming response
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible"""
        pass

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[BaseMessage]:
        """Convert dict messages to LangChain message objects"""
        converted: List[BaseMessage] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "user":
                converted.append(HumanMessage(content=content))
            elif role == "assistant":
                converted.append(AIMessage(content=content))

        return converted

    async def astream_chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        **kwargs,
    ):
        """
        Stream chat responses token by token.

        Args:
            messages: List of LangChain message objects
            tools: Optional list of LangChain tools for function calling
            **kwargs: Additional provider-specific parameters

        Yields:
            Token strings as they are generated
        """
        try:
            # Get the LLM configured for the provider
            if hasattr(self, "_handle_streaming_response"):
                llm = await self._handle_streaming_response(
                    self.llm, messages, tools, **kwargs
                )
            else:
                llm = self.llm
                if tools:
                    llm = llm.bind_tools(tools)

            # Use LangChain's astream method for token-by-token streaming
            async for chunk in llm.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    # Yield each chunk as it's generated
                    yield chunk.content

                elif isinstance(chunk, str):
                    # Handle string responses
                    yield chunk

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error in streaming: {str(e)}"
