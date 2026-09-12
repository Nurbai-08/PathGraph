import json
import re
from abc import ABC, abstractmethod
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)
GEMINI_UNSUPPORTED_SCHEMA_KEYS = {
    "default",
    "maximum",
    "maxItems",
    "maxLength",
    "minimum",
    "minItems",
    "minLength",
    "title",
}


class AIProviderError(Exception):
    pass


class AIProvider(ABC):
    provider_name: str
    model: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_structured(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        raw_response = self._generate_structured_response(prompt, schema.model_json_schema())
        try:
            return validate_structured_response(raw_response, schema)
        except (json.JSONDecodeError, ValidationError):
            repair_prompt = (
                f"{prompt}\n\nYour previous response was invalid. Return only JSON "
                "matching this schema:\n"
                f"{json.dumps(schema.model_json_schema())}"
            )
            repaired = self._generate_structured_response(repair_prompt, schema.model_json_schema())
            try:
                return validate_structured_response(repaired, schema)
            except (json.JSONDecodeError, ValidationError) as error:
                raise AIProviderError(
                    "The provider returned invalid structured output twice."
                ) from error

    @abstractmethod
    def _generate_structured_response(self, prompt: str, schema: dict[str, object]) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError


class OllamaProvider(AIProvider):
    provider_name = "ollama"

    def __init__(self, base_url: str, model: str, embedding_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model

    def generate(self, prompt: str) -> str:
        return self._generate(prompt, None)

    def _generate_structured_response(self, prompt: str, schema: dict[str, object]) -> str:
        return self._generate(prompt, schema)

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={"model": self.embedding_model, "input": text},
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings", [])
        if not embeddings:
            raise AIProviderError("Ollama returned no embedding.")
        return [float(value) for value in embeddings[0]]

    def health_check(self) -> bool:
        try:
            return httpx.get(
                f"{self.base_url}/api/tags", timeout=settings.ai_timeout_seconds
            ).is_success
        except httpx.HTTPError:
            return False

    def _generate(self, prompt: str, schema: dict[str, object] | None) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if schema:
            payload["format"] = schema
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        result = response.json().get("response")
        if not isinstance(result, str):
            raise AIProviderError("Ollama returned no generated text.")
        return result


class GeminiProvider(AIProvider):
    provider_name = "gemini"
    api_url = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str, embedding_model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.embedding_model = embedding_model

    def generate(self, prompt: str) -> str:
        return self._generate(prompt, None)

    def _generate_structured_response(self, prompt: str, schema: dict[str, object]) -> str:
        return self._generate(prompt, gemini_response_schema(schema))

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self.api_url}/models/{self.embedding_model}:embedContent",
            headers=self._headers(),
            json={
                "model": f"models/{self.embedding_model}",
                "content": {"parts": [{"text": text}]},
                "taskType": "SEMANTIC_SIMILARITY",
            },
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        values = response.json().get("embedding", {}).get("values", [])
        if not values:
            raise AIProviderError("Gemini returned no embedding.")
        return [float(value) for value in values]

    def health_check(self) -> bool:
        try:
            return httpx.get(
                f"{self.api_url}/models/{self.model}",
                headers=self._headers(),
                timeout=settings.ai_timeout_seconds,
            ).is_success
        except httpx.HTTPError:
            return False

    def _generate(self, prompt: str, schema: dict[str, object] | None) -> str:
        payload: dict[str, object] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            },
        }
        if schema:
            generation_config = payload["generationConfig"]
            assert isinstance(generation_config, dict)
            generation_config.update(
                {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                }
            )
        response = httpx.post(
            f"{self.api_url}/models/{self.model}:generateContent",
            headers=self._headers(),
            json=payload,
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise AIProviderError("Gemini returned no generated text.") from error

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}


def validate_structured_response(raw_response: str, schema: type[SchemaT]) -> SchemaT:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip())
    return schema.model_validate(json.loads(cleaned))


def gemini_response_schema(value: object) -> object:
    """Keep the JSON Schema subset accepted by Gemini structured output."""
    if isinstance(value, dict):
        return {
            key: gemini_response_schema(item)
            for key, item in value.items()
            if key not in GEMINI_UNSUPPORTED_SCHEMA_KEYS
        }
    if isinstance(value, list):
        return [gemini_response_schema(item) for item in value]
    return value
