import httpx

from app.services.ai.provider import AIError, AIProvider, AIRawResponse


class AnthropicProvider(AIProvider):
    name = "anthropic"
    url = "https://api.anthropic.com/v1/messages"

    async def complete(self, system: str, user: str, max_tokens: int = 2000) -> AIRawResponse:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(self.url, json=body, headers=headers)
        except httpx.HTTPError as e:
            raise AIError(f"Anthropic request failed: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise AIError(f"Anthropic returned HTTP {r.status_code}")
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        return AIRawResponse(text, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
