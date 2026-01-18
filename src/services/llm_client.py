"""LLM client wrapper for Anthropic structured outputs."""

from typing import TypeVar

from anthropic import Anthropic, APIError
from pydantic import BaseModel

from src.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClientError(Exception):
    """Raised when LLM extraction fails."""

    pass


class LLMClient:
    """Anthropic client wrapper with structured output support.

    Uses client.beta.messages.parse with Pydantic models for
    guaranteed schema-valid extraction output.
    """

    def __init__(self, client: Anthropic | None = None):
        """Initialize LLM client.

        Args:
            client: Optional Anthropic client for dependency injection.
                   If not provided, creates one from settings.
        """
        if client is not None:
            self._client = client
        elif settings.anthropic_api_key:
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        else:
            # Allow initialization without API key for testing
            self._client = None

    async def extract(self, prompt: str, response_model: type[T]) -> T:
        """Extract structured data from text using LLM.

        Args:
            prompt: The user prompt containing text to extract from
            response_model: Pydantic model defining the output schema

        Returns:
            Parsed response matching the response_model type

        Raises:
            LLMClientError: If extraction fails
        """
        if self._client is None:
            raise LLMClientError(
                "Anthropic client not initialized. "
                "Set ANTHROPIC_API_KEY environment variable."
            )

        try:
            response = self._client.beta.messages.parse(
                model=settings.anthropic_model,
                max_tokens=4096,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=response_model,
            )
            return response.parsed_output
        except APIError as e:
            raise LLMClientError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise LLMClientError(f"Extraction failed: {e}") from e
