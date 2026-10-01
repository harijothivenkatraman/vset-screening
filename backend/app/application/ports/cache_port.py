"""Port for caching."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class CachePort(ABC):
    """Generic key-value cache with TTL."""
    
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value by key. Returns None if not found or expired."""
        ...
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set value with optional TTL. If ttl_seconds is None, use default TTL."""
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a cached value."""
        ...
