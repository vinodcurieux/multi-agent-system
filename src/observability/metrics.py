"""
Prometheus metrics for monitoring application performance.
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from typing import Optional
from src.config import settings

# Application info
app_info = Info("app_info", "Application information")
app_info.info({
    "name": settings.APP_NAME,
    "version": settings.APP_VERSION,
    "environment": settings.ENVIRONMENT,
})

# API Request Metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

api_requests_in_progress = Gauge(
    "api_requests_in_progress",
    "Number of API requests currently being processed",
    ["method", "endpoint"],
)

# Agent Metrics
agent_invocations_total = Counter(
    "agent_invocations_total",
    "Total number of agent invocations",
    ["agent_name", "status"],
)

agent_duration_seconds = Histogram(
    "agent_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

agent_errors_total = Counter(
    "agent_errors_total",
    "Total number of agent errors",
    ["agent_name", "error_type"],
)

# LLM Metrics
llm_requests_total = Counter(
    "llm_requests_total",
    "Total number of LLM API requests",
    ["model", "status"],
)

llm_tokens_used_total = Counter(
    "llm_tokens_used_total",
    "Total number of tokens used",
    ["model", "token_type"],  # token_type: prompt, completion, total
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
)

# Database Metrics
db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["operation", "table", "status"],
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
)

db_connections_pool_size = Gauge(
    "db_connections_pool_size",
    "Database connection pool size",
)

# Session Metrics
active_sessions_total = Gauge(
    "active_sessions_total",
    "Number of active sessions",
)

session_operations_total = Counter(
    "session_operations_total",
    "Total number of session operations",
    ["operation", "status"],  # operation: create, get, update, delete
)

session_duration_seconds = Histogram(
    "session_duration_seconds",
    "Session lifetime duration in seconds",
    buckets=(60, 300, 600, 1800, 3600, 7200),  # 1m to 2h
)

# Vector Store Metrics
vector_store_queries_total = Counter(
    "vector_store_queries_total",
    "Total number of vector store queries",
    ["collection", "status"],
)

vector_store_query_duration_seconds = Histogram(
    "vector_store_query_duration_seconds",
    "Vector store query duration in seconds",
    ["collection"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

# Conversation Metrics
conversations_total = Counter(
    "conversations_total",
    "Total number of conversations",
    ["status"],  # status: completed, escalated, error
)

conversation_turns_total = Counter(
    "conversation_turns_total",
    "Total number of conversation turns",
)

conversation_duration_seconds = Histogram(
    "conversation_duration_seconds",
    "Conversation duration in seconds",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

supervisor_iterations_total = Histogram(
    "supervisor_iterations_total",
    "Number of supervisor iterations per conversation",
    buckets=(1, 2, 3, 4, 5, 10),
)


def get_metrics() -> bytes:
    """
    Generate Prometheus metrics in text format.

    Returns:
        Metrics in Prometheus exposition format
    """
    return generate_latest()


class MetricsMiddleware:
    """
    Middleware to automatically track request metrics.
    To be used with FastAPI.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            method = scope["method"]
            path = scope["path"]

            # Track in-progress requests
            api_requests_in_progress.labels(method=method, endpoint=path).inc()

            try:
                await self.app(scope, receive, send)
            finally:
                # Decrement in-progress counter
                api_requests_in_progress.labels(method=method, endpoint=path).dec()
