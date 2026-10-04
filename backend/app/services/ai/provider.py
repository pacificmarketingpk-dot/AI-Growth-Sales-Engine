"""AIProvider interface. Business logic only talks to this interface."""
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# Approximate USD per 1M tokens (input, output). Used for "estimated cost" only; edit as pricing changes.
PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-opus-4-5": (5.00, 25.00),
}


class AIError(Exception):
    """Raised when the provider is unreachable or returns unusable output."""


class AINotConfigured(AIError):
    pass


@dataclass
class AIRawResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class AIResult:
    data: BaseModel
    provider: str
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def estimated_cost(self) -> float:
        rate_in, rate_out = PRICING.get(self.model, (0.0, 0.0))
        return round(self.input_tokens / 1e6 * rate_in + self.output_tokens / 1e6 * rate_out, 6)


class AIProvider(ABC):
    name: str = "base"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    async def complete(self, system: str, user: str, max_tokens: int = 2000) -> AIRawResponse:
        ...

    async def generate(self, system: str, user: str, schema: type[T], retries: int = 2) -> AIResult:
        """Call the model and return a validated object. Malformed output is retried, never saved."""
        if not self.configured:
            raise AINotConfigured(f"{self.name} API key is not configured")
        tokens_in = tokens_out = 0
        prompt = user
        last_error = ""
        for attempt in range(retries + 1):
            raw = await self.complete(system, prompt)
            tokens_in += raw.input_tokens
            tokens_out += raw.output_tokens
            try:
                obj = schema.model_validate(extract_json(raw.text))
                return AIResult(obj, self.name, self.model, tokens_in, tokens_out)
            except (ValueError, ValidationError) as e:
                last_error = str(e)[:1500]
                log.warning("AI output failed validation (attempt %s): %s", attempt + 1, last_error[:300])
                prompt = (f"{user}\n\nYour previous answer was rejected by the validator:\n{last_error}\n"
                          "Return corrected JSON only, matching the schema exactly.")
        raise AIError(f"AI output failed validation after {retries + 1} attempts: {last_error[:300]}")


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("response did not contain a JSON object")
        return json.loads(text[start:end + 1])
