"""Claude API integration — wraps Anthropic SDK with retry, cost tracking, and error handling.

Per spec Section 13.2: retry up to 3 times with exponential backoff (1s, 2s, 4s).
Per spec Section 9.1: track tokens and calculate cost after every call.
"""

import asyncio
import logging
from dataclasses import dataclass

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Structured response from Claude API call."""
    content: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    model_used: str


async def call_claude(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int | None = None,
    temperature: float = 0.3,
    model: str | None = None,
) -> ClaudeResponse:
    """Call Claude API with retry logic per Section 13.2.

    Returns ClaudeResponse with content, token counts, and cost.
    Raises RuntimeError after 3 failed retries.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    model_name = model or settings.CLAUDE_MODEL
    max_tok = max_tokens or settings.CLAUDE_MAX_TOKENS

    last_error = None
    for attempt in range(3):
        try:
            response = await client.messages.create(
                model=model_name,
                max_tokens=max_tok,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
            )

            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens
            cost_usd = (
                tokens_input * settings.COST_PER_INPUT_TOKEN
                + tokens_output * settings.COST_PER_OUTPUT_TOKEN
            )

            return ClaudeResponse(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                model_used=model_name,
            )

        except anthropic.APIError as e:
            last_error = e
            backoff = 2**attempt  # 1s, 2s, 4s
            logger.warning(f"Claude API error (attempt {attempt + 1}/3): {e}. Retrying in {backoff}s.")
            await asyncio.sleep(backoff)

    raise RuntimeError(f"Claude API failed after 3 retries: {last_error}")
