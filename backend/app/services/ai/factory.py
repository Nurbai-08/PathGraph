from app.core.errors import AppError
from app.models.ai import AISetting
from app.services.ai.credentials import CredentialCipher
from app.services.ai.providers import AIProvider, GeminiProvider, OllamaProvider


def create_provider(setting: AISetting) -> AIProvider:
    if setting.provider == "ollama":
        return OllamaProvider(
            setting.base_url or "http://localhost:11434",
            setting.model,
            setting.embedding_model,
        )
    if setting.provider == "gemini":
        if not setting.api_key_encrypted:
            raise AppError(422, "GEMINI_API_KEY_REQUIRED", "Gemini requires an API key.")
        api_key = CredentialCipher().decrypt(setting.api_key_encrypted)
        return GeminiProvider(api_key, setting.model, setting.embedding_model)
    raise AppError(422, "INVALID_AI_PROVIDER", "The configured AI provider is not supported.")
