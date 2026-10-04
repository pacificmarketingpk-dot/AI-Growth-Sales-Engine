import httpx

from app.services.ai.provider import AIError, AIProvider, AIRawResponse


class OpenAIProvider(AIProvider):
    name = "openai"
    url = "https://api.openai.com/v1/chat/completions"

    async def complete(self, system: str, user: str, max_tokens: int = 2000) -> AIRawResponse:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(self.url, json=body, headers={"Authorization": f"Bearer {self.api_key}"})
        except httpx.HTTPError as e:
            raise AIError(f"OpenAI request failed: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise AIError(f"OpenAI returned HTTP {r.status_code}")
        data = r.json()
        usage = data.get("usage", {})
        return AIRawResponse(data["choices"][0]["message"]["content"] or "",
                             usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
