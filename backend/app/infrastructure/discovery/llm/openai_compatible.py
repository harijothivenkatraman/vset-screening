"""OpenAI-compatible LLM client implementing LlmPort."""
from __future__ import annotations

import logging
from typing import Any
import httpx

from app.application.ports.llm_port import LlmPort
from app.domain.exceptions import LlmUnavailableError

logger = logging.getLogger(__name__)


class OpenAICompatibleLlmAdapter(LlmPort):
    """Adapter for interacting with local LLMs (Ollama, LM Studio, vLLM) via OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        model: str = "qwen2.5:7b-instruct",
        timeout_seconds: float = 300.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def complete(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        response_schema: dict[str, Any] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        endpoint = f"{self._base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code >= 400:
                    raise LlmUnavailableError(
                        self._base_url,
                        f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return ""
                return str(choices[0].get("message", {}).get("content", "")).strip()
        except httpx.RequestError as exc:
            logger.warning("LLM request failed to '%s': %s", endpoint, exc)
            raise LlmUnavailableError(self._base_url, str(exc)) from exc

    async def is_available(self) -> bool:
        """Ping /models endpoint to verify LLM server reachability and configured model presence."""
        avail = await self.check_availability()
        return avail.get("reachable", False) and avail.get("model_available", False)

    async def check_availability(self) -> dict[str, bool]:
        """Check server reachability and model presence separately."""
        endpoint = f"{self._base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(endpoint)
                if resp.status_code != 200:
                    return {"reachable": False, "model_available": False}
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
                model_present = any(self._model == m or self._model in str(m) for m in models) if models else False
                return {"reachable": True, "model_available": model_present}
        except Exception:
            return {"reachable": False, "model_available": False}
