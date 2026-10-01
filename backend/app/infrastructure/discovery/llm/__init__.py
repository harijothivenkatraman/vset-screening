"""LLM infrastructure package."""
from app.infrastructure.discovery.llm.openai_compatible import OpenAICompatibleLlmAdapter
from app.infrastructure.discovery.llm.report_extractor import SectionBySectionExtractor

__all__ = ["OpenAICompatibleLlmAdapter", "SectionBySectionExtractor"]
