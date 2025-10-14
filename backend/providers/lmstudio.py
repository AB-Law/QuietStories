"""
LMStudio provider implementation for local LLM inference

LMStudio provides an OpenAI-compatible API for running local models.
Default endpoint: http://localhost:5101/v1
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain.schema import BaseMessage, HumanMessage
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

from .base import BaseProvider, ProviderResponse


class LMStudioProvider(BaseProvider):
    """LMStudio provider for local LLM models with OpenAI-compatible API"""

    def __init__(
        self, api_base: str = "http://localhost:5101/v1", api_key: str = "", model_name: str = "local-model"
    ):
        """
        Initialize LMStudio provider.
        
        Args:
            api_base: LMStudio server URL (default: http://localhost:5101/v1)
            api_key: API key (not required for LMStudio, but kept for compatibility)
            model_name: Name of the loaded model (can be any string for LMStudio)
        """
        super().__init__(api_base, api_key or "lm-studio", model_name)
        
        # LMStudio-specific configuration
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=api_base,
            api_key=self.api_key,  # type: ignore
            temperature=0.7,
            # LMStudio often has lower token limits for local models
            max_tokens=2048,
        )
        
        self.logger = logging.getLogger(__name__)

    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """
        Send chat request to LMStudio using OpenAI-compatible API.
        
        Args:
            messages: List of messages to send
            tools: Optional list of tools (may not be supported by all local models)
            json_schema: Optional JSON schema for structured output
            stream: Whether to stream the response
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            ProviderResponse with generated content
        """
        try:
            self.logger.debug(f"[LMStudio] Sending request to {self.api_base}")
            self.logger.debug(f"[LMStudio] Model: {self.model_name}")
            
            # Configure LLM with parameters
            llm = self.llm
            
            # Apply custom parameters
            if "temperature" in kwargs:
                llm = llm.bind(temperature=kwargs["temperature"])
            if "max_tokens" in kwargs:
                llm = llm.bind(max_tokens=kwargs["max_tokens"])
            
            # Note: Tool calling may not be supported by all local models
            # We'll try to bind tools but gracefully handle if not supported
            if tools:
                try:
                    self.logger.debug(f"[LMStudio] Attempting to bind {len(tools)} tools")
                    llm = llm.bind_tools(tools)
                except Exception as e:
                    self.logger.warning(f"[LMStudio] Tool binding not supported: {e}")
                    # Continue without tools
            
            # Handle structured output if requested
            if json_schema is not None:
                try:
                    self.logger.info("[LMStudio] Using structured output")
                    structured_llm = llm.with_structured_output(json_schema)
                    structured = await structured_llm.ainvoke(messages)
                    
                    # Convert to JSON string
                    content = json.dumps(structured) if not isinstance(structured, str) else structured
                    
                    return ProviderResponse(
                        content=content,
                        usage=self._estimate_usage(messages, content),
                        model=self.model_name,
                        tool_calls=None,
                    )
                except Exception as e:
                    self.logger.warning(f"[LMStudio] Structured output failed: {e}")
                    # Fall back to regular generation and try to parse JSON
            
            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, messages, tools, **kwargs)
            
            # Normal invocation
            self.logger.debug(f"[LMStudio] Invoking with {len(messages)} messages")
            response = await llm.ainvoke(messages)
            
            # Extract content
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            
            self.logger.debug(f"[LMStudio] Received {len(content)} characters")
            
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
                    self.logger.debug(f"[LMStudio] Extracted {len(tool_calls)} tool calls")
                except Exception as e:
                    self.logger.warning(f"[LMStudio] Failed to extract tool calls: {e}")
            
            # Get usage metadata if available, otherwise estimate
            usage = getattr(response, "usage_metadata", None)
            if not usage:
                usage = self._estimate_usage(messages, content)
            
            return ProviderResponse(
                content=content,
                usage=usage,
                model=self.model_name,
                tool_calls=tool_calls,
            )

        except Exception as e:
            self.logger.error(f"[LMStudio] Error: {e}")
            raise Exception(f"LMStudio API error: {e}. Make sure LMStudio is running on {self.api_base}")

    def _estimate_usage(self, messages: List[BaseMessage], content: str) -> Dict[str, int]:
        """
        Estimate token usage for local models that don't provide usage stats.
        
        Args:
            messages: Input messages
            content: Generated content
            
        Returns:
            Dictionary with estimated token counts
        """
        # Rough estimation: ~4 characters per token on average
        prompt_text = " ".join([
            msg.content if hasattr(msg, "content") else str(msg) 
            for msg in messages
        ])
        
        prompt_tokens = len(prompt_text) // 4
        completion_tokens = len(content) // 4
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    async def _handle_streaming_response(self, llm, messages, tools, **kwargs):
        """Handle streaming responses from LMStudio"""
        # For now, return the LLM for streaming
        # This can be enhanced with proper streaming support
        self.logger.debug("[LMStudio] Streaming mode enabled")
        return llm

    async def health_check(self) -> bool:
        """
        Check if LMStudio server is accessible and responding.
        
        Returns:
            True if LMStudio is accessible, False otherwise
        """
        try:
            self.logger.info(f"[LMStudio] Health check to {self.api_base}")
            
            # Simple health check with minimal message
            test_message = HumanMessage(content="Hi")
            response = await self.llm.ainvoke([test_message])
            
            self.logger.info("[LMStudio] Health check passed ✓")
            return True
            
        except Exception as e:
            self.logger.error(f"[LMStudio] Health check failed: {e}")
            self.logger.error(f"Make sure LMStudio is running on {self.api_base}")
            return False

