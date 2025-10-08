"""
Generic HTTP provider for OpenAI-compatible endpoints using LangChain
"""

from typing import Any, Dict, List, Optional, Union
import json
import logging
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage
from langchain.tools import BaseTool
from .base import BaseProvider, ProviderResponse


class GenericProvider(BaseProvider):
    """Generic provider for OpenAI-compatible endpoints using LangChain"""
    
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
        """Send chat request to generic OpenAI-compatible endpoint using LangChain"""
        
        try:
            logger = logging.getLogger(__name__)
            # Configure LLM with parameters
            llm = self.llm
            if "temperature" in kwargs:
                llm = llm.bind(temperature=kwargs["temperature"])
            if "max_tokens" in kwargs:
                llm = llm.bind(max_tokens=kwargs["max_tokens"])

            # Bind tools first if any (LangChain guidance)
            if tools:
                llm = llm.bind_tools(tools)

            # If a json_schema was provided, enforce structured output
            if json_schema is not None:
                # with_structured_output can take a dict JSON schema
                structured_llm = llm.with_structured_output(json_schema)
                logger.info("[Provider] with_structured_output → invoking model")
                logger.info(f"[Provider] Messages: {messages}")
                structured = await structured_llm.ainvoke(messages)
                logger.info(f"[Provider] Structured result type: {type(structured)}")
                # Ensure we return content as a JSON string so downstream parsers work
                content = json.dumps(structured)
                return ProviderResponse(
                    content=content,
                    usage=getattr(structured, 'usage_metadata', None),
                    model=self.model_name,
                    tool_calls=None,
                )

            # Otherwise normal invocation
            logger.info("[Provider] Normal ainvoke without structured output")
            logger.info(f"[Provider] Messages: {messages}")
            response = await llm.ainvoke(messages)
            logger.info(f"[Provider] Response class: {type(response)}")

            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, messages, tools, **kwargs)

            # Extract content and tool calls
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"[Provider] Content preview: {content[:300]}")
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
            raise Exception(f"Generic API error: {e}")
    
    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses"""
        # For now, return the LLM for streaming
        # This can be enhanced with proper streaming support
        return llm
    
    async def health_check(self) -> bool:
        """Check if the generic endpoint is accessible"""
        try:
            # Simple health check by trying to invoke the model
            test_message = HumanMessage(content="Hello")
            await self.llm.ainvoke([test_message])
            return True
        except Exception:
            return False
