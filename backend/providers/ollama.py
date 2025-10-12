"""
Ollama provider implementation using LangChain
"""

from typing import Any, Dict, List, Optional, Union

from langchain.schema import BaseMessage
from langchain.tools import BaseTool
from langchain_community.llms import Ollama

from .base import BaseProvider, ProviderResponse


class OllamaProvider(BaseProvider):
    """Ollama provider for local LLM models using LangChain"""

    def __init__(self, api_base: str, api_key: str, model_name: str):
        super().__init__(api_base, api_key, model_name)
        self.llm = Ollama(
            model=model_name,
            base_url=api_base,
            temperature=0.7,
            num_predict=2000,
        )

    async def chat(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[ProviderResponse, Any]:
        """Send chat request to Ollama using LangChain"""

        try:
            # Configure LLM with parameters
            llm = self.llm
            if "temperature" in kwargs:
                llm = llm.bind(temperature=kwargs["temperature"])
            if "max_tokens" in kwargs:
                llm = llm.bind(num_predict=kwargs["max_tokens"])

            # Convert messages to prompt format
            prompt = self._format_messages(messages)

            # Add JSON schema instruction if provided
            if json_schema:
                prompt += "\n\nRespond with valid JSON only."

            # Handle streaming
            if stream:
                return self._handle_streaming_response(llm, prompt, **kwargs)

            # Get response
            response = await llm.ainvoke(prompt)
            content = response if isinstance(response, str) else str(response)

            return ProviderResponse(
                content=content,
                usage={
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(content.split()),
                    "total_tokens": len(prompt.split()) + len(content.split()),
                },
                model=self.model_name,
            )

        except Exception as e:
            raise Exception(f"Ollama API error: {e}")

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to Ollama prompt format"""
        formatted = []
        for msg in messages:
            if hasattr(msg, "content"):
                content = msg.content
            else:
                content = str(msg)

            if hasattr(msg, "__class__"):
                class_name = msg.__class__.__name__
                if "System" in class_name:
                    formatted.append(f"System: {content}")
                elif "Human" in class_name:
                    formatted.append(f"Human: {content}")
                elif "AI" in class_name or "Assistant" in class_name:
                    formatted.append(f"Assistant: {content}")
                else:
                    formatted.append(f"User: {content}")
            else:
                formatted.append(f"User: {content}")

        return "\n\n".join(formatted) + "\n\nAssistant:"

    async def _handle_streaming_response(self, llm, prompt, **kwargs):
        """Handle streaming responses"""
        # For now, return the LLM for streaming
        # This can be enhanced with proper streaming support
        return llm

    async def health_check(self) -> bool:
        """Check if Ollama is accessible"""
        try:
            # Simple health check by trying to invoke the model
            test_prompt = "Hello"
            await self.llm.ainvoke(test_prompt)
            return True
        except Exception:
            return False
