"""OpenAI LLM provider implementation."""
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a completion using OpenAI API."""
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            params["max_tokens"] = max_tokens

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Add any additional kwargs
        params.update(kwargs)

        response = await self.client.chat.completions.create(**params)

        message = response.choices[0].message

        result = {
            "content": message.content,
            "tool_calls": None,
            "usage": self.extract_usage(response),
            "finish_reason": response.choices[0].finish_reason,
        }

        if message.tool_calls:
            result["tool_calls"] = self.format_tool_calls(message.tool_calls)

        return result

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate a streaming completion using OpenAI API."""
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            params["max_tokens"] = max_tokens

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Add any additional kwargs
        params.update(kwargs)

        stream = await self.client.chat.completions.create(**params)

        async for chunk in stream:
            delta = chunk.choices[0].delta

            result = {
                "content": delta.content if delta.content else None,
                "tool_calls": None,
                "finish_reason": chunk.choices[0].finish_reason,
            }

            if delta.tool_calls:
                result["tool_calls"] = self.format_tool_calls(delta.tool_calls)

            yield result

    def format_tool_calls(self, tool_calls: Any) -> List[Dict[str, Any]]:
        """Convert OpenAI tool calls to standard format (already in correct format)."""
        formatted = []

        for tc in tool_calls:
            formatted.append({
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })

        return formatted

    def extract_usage(self, response: Any) -> Dict[str, int]:
        """Extract token usage from OpenAI response."""
        if not response.usage:
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }

        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
