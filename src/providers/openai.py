"""
OpenAI provider implementation using LangChain
"""

import json
from typing import Any, Dict, List, Optional, Union
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage
from langchain.tools import BaseTool
# from langchain.callbacks import AsyncCallbackHandler  # Not needed for now
from .base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    """OpenAI API provider using LangChain"""
    
    def __init__(self, api_base: str, api_key: str, model_name: str):
        super().__init__(api_base, api_key, model_name)
        self.llm = ChatOpenAI(
            model=model_name,
            openai_api_base=api_base,
            openai_api_key=api_key,
            temperature=0.7,
            max_tokens=2000,
        )
    
    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to OpenAI API using LangChain"""
        
        try:
            # Configure LLM with parameters
            llm = self.llm.copy()
            if "temperature" in kwargs:
                llm.temperature = kwargs["temperature"]
            if "max_tokens" in kwargs:
                llm.max_tokens = kwargs["max_tokens"]
            
            # Handle tools if provided
            if tools:
                # Use LangChain's tool calling
                llm_with_tools = llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)
            
            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, messages, tools, **kwargs)
            
            # Extract content and tool calls
            content = response.content if hasattr(response, 'content') else str(response)
            tool_calls = None
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_calls = [
                    {
                        "id": tc.get("id"),
                        "type": tc.get("type"),
                        "function": {
                            "name": tc.get("name"),
                            "arguments": tc.get("args")
                        }
                    }
                    for tc in response.tool_calls
                ]
            
            return ProviderResponse(
                content=content,
                usage=getattr(response, 'usage_metadata', None),
                model=self.model_name,
                tool_calls=tool_calls,
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses"""
        # For now, return the LLM for streaming
        # This can be enhanced with proper streaming support
        return llm
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # Simple health check by trying to invoke the model
            test_message = [{"role": "user", "content": "Hello"}]
            messages = self._convert_messages(test_message)
            await self.llm.ainvoke(messages)
            return True
        except Exception:
            return False
