"""Port for LLM completion (OpenAI-compatible API)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class LlmPort(ABC):
    """Send completion requests to a local LLM server."""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        response_schema: dict[str, Any] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        """Send a chat completion request. Returns the response text.
        
        Args:
            prompt: The user message.
            system_prompt: System message for context.
            response_schema: JSON schema for structured output (if supported).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0 = deterministic).
        
        Raises:
            LlmUnavailableError: If the LLM server is not reachable.
        """
        ...
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM server and configured model are reachable."""
        ...
