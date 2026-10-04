from app.config import get_settings
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.demo_provider import DemoProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.provider import AIProvider

PROVIDERS = {"openai": OpenAIProvider, "anthropic": AnthropicProvider}


def get_provider(name: str = "", model: str = "") -> AIProvider:
    s = get_settings()
    name = (name or s.ai_provider or "anthropic").lower()
    if name == "openai":
        return OpenAIProvider(s.openai_api_key, model or s.openai_model)
    return AnthropicProvider(s.anthropic_api_key, model or s.anthropic_model)


def provider_for_user(user_settings, is_demo: bool = False) -> AIProvider:
    if is_demo:
        return DemoProvider()
    return get_provider(getattr(user_settings, "ai_provider", "") or "", getattr(user_settings, "ai_model", "") or "")


def provider_status() -> dict:
    s = get_settings()
    return {
        "default_provider": s.ai_provider,
        "providers": {
            "openai": {"configured": bool(s.openai_api_key), "default_model": s.openai_model},
            "anthropic": {"configured": bool(s.anthropic_api_key), "default_model": s.anthropic_model},
        },
    }
