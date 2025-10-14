"""
OpenAI provider implementation using LangChain
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

from langchain.schema import BaseMessage
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

# from langchain.callbacks import AsyncCallbackHandler  # Not needed for now
from .base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    """OpenAI API provider using LangChain"""

    def __init__(self, api_base: str, api_key: str, model_name: str):
        super().__init__(api_base, api_key, model_name)
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
        """Send chat request to OpenAI API using LangChain"""

        # Log the LLM call
        call_id = self._log_llm_call(messages, tools, **kwargs)
        start_time = time.time()

        try:
            # Configure LLM with parameters
            llm = self.llm
            if "temperature" in kwargs:
                llm = llm.bind(temperature=kwargs["temperature"])
            if "max_tokens" in kwargs:
                llm = llm.bind(max_tokens=kwargs["max_tokens"])

            # Handle tools if provided
            if tools:
                # Use LangChain's tool calling
                llm_with_tools = llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)

            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_llm_response(call_id, response, duration_ms)

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
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_llm_response(call_id, None, duration_ms, error=e)
            raise Exception(f"OpenAI API error: {e}")

    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses"""
        # Return the LLM configured for streaming
        if tools:
            return llm.bind_tools(tools)
        return llm

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # Simple health check by trying to invoke the model
            from langchain.schema import HumanMessage

            test_message = HumanMessage(content="Hello")
            await self.llm.ainvoke([test_message])
            return True
        except Exception:
            return False
