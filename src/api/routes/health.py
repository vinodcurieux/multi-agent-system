"""
Health check endpoints.
Provides system health status and readiness checks.
"""
from fastapi import APIRouter, Response
from datetime import datetime
import time

from src.config import settings
from src.api.models import HealthResponse, ServiceStatus
from src.observability.logging_config import get_logger
from src.observability import metrics

logger = get_logger(__name__)
router = APIRouter()


def check_database() -> ServiceStatus:
    """Check database connectivity."""
    start_time = time.time()

    try:
        from src.database.connection import connect_db

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()

        duration_ms = (time.time() - start_time) * 1000

        return ServiceStatus(
            name="database",
            status="healthy",
            details="SQLite connection successful",
            response_time_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Database health check failed: {e}")

        return ServiceStatus(
            name="database",
            status="unhealthy",
            details=f"Connection failed: {str(e)}",
            response_time_ms=duration_ms,
        )


def check_vector_store() -> ServiceStatus:
    """Check vector store connectivity."""
    start_time = time.time()

    try:
        from src.rag.vector_store import get_vector_store

        vector_store = get_vector_store()
        count = vector_store.get_collection_count()

        duration_ms = (time.time() - start_time) * 1000

        return ServiceStatus(
            name="vector_store",
            status="healthy",
            details=f"ChromaDB accessible ({count} documents)",
            response_time_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Vector store health check failed: {e}")

        return ServiceStatus(
            name="vector_store",
            status="unhealthy",
            details=f"Connection failed: {str(e)}",
            response_time_ms=duration_ms,
        )


def check_llm() -> ServiceStatus:
    """Check LLM client availability."""
    start_time = time.time()

    try:
        from src.utils.llm_client import get_llm_client

        client = get_llm_client()

        duration_ms = (time.time() - start_time) * 1000

        return ServiceStatus(
            name="llm",
            status="healthy",
            details=f"OpenAI client initialized (model: {client.model})",
            response_time_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"LLM health check failed: {e}")

        return ServiceStatus(
            name="llm",
            status="unhealthy",
            details=f"Client initialization failed: {str(e)}",
            response_time_ms=duration_ms,
        )


def check_workflow() -> ServiceStatus:
    """Check LangGraph workflow availability."""
    start_time = time.time()

    try:
        from src.graph.workflow import get_workflow

        workflow = get_workflow()

        duration_ms = (time.time() - start_time) * 1000

        return ServiceStatus(
            name="workflow",
            status="healthy",
            details="LangGraph workflow compiled",
            response_time_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Workflow health check failed: {e}")

        return ServiceStatus(
            name="workflow",
            status="unhealthy",
            details=f"Workflow compilation failed: {str(e)}",
            response_time_ms=duration_ms,
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks all system dependencies:
    - Database connectivity
    - Vector store accessibility
    - LLM client availability
    - Workflow compilation

    Returns:
        HealthResponse with status of all services
    """
    logger.debug("Health check requested")

    # Check all services
    services = [
        check_database(),
        check_vector_store(),
        check_llm(),
        check_workflow(),
    ]

    # Determine overall status
    unhealthy_services = [s for s in services if s.status == "unhealthy"]

    if len(unhealthy_services) == 0:
        overall_status = "healthy"
    elif len(unhealthy_services) < len(services):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    logger.info(f"Health check: {overall_status} ({len(unhealthy_services)}/{len(services)} unhealthy)")

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get("/health/live", include_in_schema=False)
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready", include_in_schema=False)
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the application is ready to serve traffic.
    Checks if critical dependencies are available.
    """
    # Check critical services only
    db_status = check_database()
    workflow_status = check_workflow()

    if db_status.status == "healthy" and workflow_status.status == "healthy":
        return {"status": "ready"}
    else:
        return Response(
            content='{"status": "not ready"}',
            status_code=503,
            media_type="application/json",
        )


@router.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    metrics_data = metrics.get_metrics()

    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
