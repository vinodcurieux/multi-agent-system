"""
OpenTelemetry tracing with Phoenix integration.
Provides decorators and utilities for tracing agent execution.
"""
from functools import wraps
import time
from typing import Any, Callable, Dict, Optional
from opentelemetry.trace import get_current_span, Status, StatusCode, Tracer
from opentelemetry.trace import get_tracer_provider
from src.config import settings
from src.observability.logging_config import get_logger

logger = get_logger(__name__)

# Global tracer instance
_tracer: Optional[Tracer] = None


def initialize_tracing() -> Optional[Tracer]:
    """
    Initialize Phoenix tracing if enabled.

    Returns:
        Tracer instance if tracing is enabled, None otherwise
    """
    global _tracer

    if not settings.PHOENIX_ENABLED:
        logger.info("Phoenix tracing is disabled")
        return None

    try:
        from phoenix.otel import register

        tracer_provider = register(
            project_name=settings.PHOENIX_PROJECT_NAME,
            endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT,
            auto_instrument=True,
        )

        _tracer = tracer_provider.get_tracer(__name__)
        logger.info(
            f"Phoenix tracing initialized: project={settings.PHOENIX_PROJECT_NAME}, "
            f"endpoint={settings.PHOENIX_COLLECTOR_ENDPOINT}"
        )
        return _tracer

    except ImportError:
        logger.warning(
            "Phoenix tracing libraries not installed. "
            "Install with: pip install arize-phoenix-otel openinference-instrumentation-openai"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Phoenix tracing: {e}")
        return None


def get_tracer() -> Optional[Tracer]:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance if available, None otherwise
    """
    global _tracer
    if _tracer is None:
        _tracer = initialize_tracing()
    return _tracer


def trace_agent(func: Callable) -> Callable:
    """
    Decorator to wrap agent functions in a Phoenix span with metadata.

    Usage:
        @trace_agent
        def my_agent_node(state):
            # agent logic
            return updated_state

    Args:
        func: Agent function to wrap

    Returns:
        Wrapped function with tracing
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Get state from first argument if available
        state = args[0] if args else {}
        agent_name = func.__name__

        tracer = get_tracer()

        # If tracing is not enabled, just execute the function
        if tracer is None:
            return func(*args, **kwargs)

        # Start a new span
        with tracer.start_as_current_span(agent_name) as span:
            # Add standard metadata
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.type", agent_name.replace("_node", "").replace("_agent", ""))

            # Add state-based attributes if state is a dict
            if isinstance(state, dict):
                span.set_attribute("user.id", state.get("customer_id", "unknown"))
                span.set_attribute("policy.number", state.get("policy_number", "unknown"))
                span.set_attribute("claim.id", state.get("claim_id", "unknown"))
                span.set_attribute("task", state.get("task", "none"))
                span.set_attribute("iteration", state.get("n_iteration", 0))

                # Add session info
                if "session_id" in state:
                    span.set_attribute("session.id", state.get("session_id"))

            span.set_attribute("timestamp", time.time())

            start_time = time.time()

            try:
                # Execute the agent function
                result = func(*args, **kwargs)

                # Record execution metadata
                duration = time.time() - start_time
                span.set_attribute("execution.duration_sec", duration)

                # Add result metadata if result is a dict
                if isinstance(result, dict):
                    span.set_attribute("result.keys", list(result.keys()))
                    if "next_agent" in result:
                        span.set_attribute("routing.next_agent", result["next_agent"])
                    if "end_conversation" in result:
                        span.set_attribute("conversation.ended", result["end_conversation"])

                span.set_status(Status(StatusCode.OK))
                return result

            except Exception as e:
                # Record exception
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
                raise

    return wrapper


def trace_function(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Generic decorator to trace any function with custom attributes.

    Usage:
        @trace_function(name="database_query", attributes={"db.operation": "select"})
        def query_database(query):
            # query logic
            return results

    Args:
        name: Span name (defaults to function name)
        attributes: Additional attributes to add to span

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            tracer = get_tracer()

            # If tracing is not enabled, just execute the function
            if tracer is None:
                return func(*args, **kwargs)

            span_name = name or func.__name__

            with tracer.start_as_current_span(span_name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                start_time = time.time()

                try:
                    result = func(*args, **kwargs)

                    duration = time.time() - start_time
                    span.set_attribute("execution.duration_sec", duration)
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper

    return decorator


def add_span_attribute(key: str, value: Any) -> None:
    """
    Add an attribute to the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    try:
        span = get_current_span()
        if span.is_recording():
            span.set_attribute(key, value)
    except Exception as e:
        logger.debug(f"Failed to add span attribute: {e}")


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Event attributes
    """
    try:
        span = get_current_span()
        if span.is_recording():
            span.add_event(name, attributes or {})
    except Exception as e:
        logger.debug(f"Failed to add span event: {e}")
