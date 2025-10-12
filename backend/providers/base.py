"""
Abstract base class for LLM providers using LangChain
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain.tools import BaseTool
from pydantic import BaseModel

# from langchain.schema.output import LLMResult  # Not needed for now


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
