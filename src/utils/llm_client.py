"""
OpenAI client wrapper with tracing and error handling.
"""
from openai import OpenAI
import json
from typing import List, Dict, Any, Optional
import time

from src.config import settings
from src.observability.logging_config import get_logger
from src.observability.tracing import trace_function
from src.observability import metrics

logger = get_logger(__name__)


class LLMClient:
    """
    Wrapper around OpenAI client with tracing, metrics, and error handling.
    """

    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        self.model = settings.OPENAI_MODEL
        logger.info(f"LLM client initialized with model: {self.model}")

    @trace_function(name="llm_completion", attributes={"llm.provider": "openai"})
    def run_llm(
        self,
        prompt: str,
        tools: Optional[List[Dict]] = None,
        tool_functions: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Run an LLM request with optional tool calling support.

        Args:
            prompt: The system or user prompt to send
            tools: Tool schema list for model function calling
            tool_functions: Mapping of tool names to Python functions
            model: Model name to use (defaults to config model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Final LLM response text
        """
        model = model or self.model
        start_time = time.time()

        try:
            # Step 1: Initial LLM call
            logger.debug(f"Making LLM request to {model}")
            metrics.llm_requests_total.labels(model=model, status="started").inc()

            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": prompt}],
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            message = response.choices[0].message

            # Track token usage
            if hasattr(response, "usage") and response.usage:
                metrics.llm_tokens_used_total.labels(
                    model=model, token_type="prompt"
                ).inc(response.usage.prompt_tokens)
                metrics.llm_tokens_used_total.labels(
                    model=model, token_type="completion"
                ).inc(response.usage.completion_tokens)
                metrics.llm_tokens_used_total.labels(
                    model=model, token_type="total"
                ).inc(response.usage.total_tokens)

            logger.debug(f"Initial LLM response: {message}")

            # Step 2: If no tools or no tool calls, return simple model response
            if not getattr(message, "tool_calls", None):
                duration = time.time() - start_time
                metrics.llm_request_duration_seconds.labels(model=model).observe(duration)
                metrics.llm_requests_total.labels(model=model, status="success").inc()
                return message.content

            # Step 3: Handle tool calls dynamically
            if not tool_functions:
                logger.warning("Tool calls requested but no tool functions provided")
                return message.content + "\n\n⚠️ No tool functions provided to execute tool calls."

            logger.info(f"Processing {len(message.tool_calls)} tool call(s)")
            tool_messages = []

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")
                tool_fn = tool_functions.get(func_name)

                logger.debug(f"Calling tool: {func_name} with args: {args}")

                try:
                    result = tool_fn(**args) if tool_fn else {"error": f"Tool '{func_name}' not implemented."}
                    logger.debug(f"Tool {func_name} result: {result}")
                except Exception as e:
                    logger.error(f"Tool {func_name} failed: {e}", exc_info=True)
                    result = {"error": str(e)}

                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            # Step 4: Second pass — send tool outputs back to the model
            logger.debug("Sending tool results back to LLM")
            followup_messages = [
                {"role": "system", "content": prompt},
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        } for tc in message.tool_calls
                    ],
                },
                *tool_messages,
            ]

            final_response = self.client.chat.completions.create(
                model=model,
                messages=followup_messages,
                temperature=temperature,
            )

            # Track additional token usage
            if hasattr(final_response, "usage") and final_response.usage:
                metrics.llm_tokens_used_total.labels(
                    model=model, token_type="prompt"
                ).inc(final_response.usage.prompt_tokens)
                metrics.llm_tokens_used_total.labels(
                    model=model, token_type="completion"
                ).inc(final_response.usage.completion_tokens)
                metrics.llm_tokens_used_total.labels(
                    model=model, token_type="total"
                ).inc(final_response.usage.total_tokens)

            duration = time.time() - start_time
            metrics.llm_request_duration_seconds.labels(model=model).observe(duration)
            metrics.llm_requests_total.labels(model=model, status="success").inc()

            final_content = final_response.choices[0].message.content
            logger.debug(f"Final LLM response: {final_content}")

            return final_content

        except Exception as e:
            duration = time.time() - start_time
            metrics.llm_request_duration_seconds.labels(model=model).observe(duration)
            metrics.llm_requests_total.labels(model=model, status="error").inc()
            logger.error(f"LLM request failed: {e}", exc_info=True)
            raise


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get the global LLM client instance.

    Returns:
        LLMClient instance
    """
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
