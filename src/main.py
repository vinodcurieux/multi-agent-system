"""
FastAPI application entry point.
Main application with middleware, routing, and lifecycle management.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
import uuid
import asyncio

from src.config import settings
from src.observability.logging_config import setup_logging, get_logger
from src.observability.tracing import initialize_tracing
from src.observability import metrics
from src.api.models import ErrorResponse

# Import routers
from src.api.routes import health, chat, sessions

# Setup logging
setup_logging(level=settings.LOG_LEVEL, format_type=settings.LOG_FORMAT)
logger = get_logger(__name__)


async def session_cleanup_task():
    """
    Background task to periodically clean up expired sessions.

    Runs every hour to remove expired sessions from the in-memory store.
    Redis handles cleanup automatically via TTL.
    """
    from src.session.manager import get_session_manager

    # Run cleanup every hour
    cleanup_interval = 3600  # seconds

    logger.info(f"Session cleanup task started (interval: {cleanup_interval}s)")

    while True:
        try:
            await asyncio.sleep(cleanup_interval)

            session_manager = get_session_manager()
            cleaned = session_manager.cleanup_expired()

            if cleaned > 0:
                logger.info(f"Session cleanup: removed {cleaned} expired sessions")
                metrics.session_operations_total.labels(
                    operation="cleanup",
                    status="success"
                ).inc()
            else:
                logger.debug("Session cleanup: no expired sessions found")

        except asyncio.CancelledError:
            logger.info("Session cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Session cleanup error: {e}", exc_info=True)
            metrics.session_operations_total.labels(
                operation="cleanup",
                status="error"
            ).inc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize tracing
    if settings.PHOENIX_ENABLED:
        initialize_tracing()
        logger.info("✅ Phoenix tracing initialized")
    else:
        logger.info("⚠️  Phoenix tracing disabled")

    # Initialize workflow
    try:
        from src.graph.workflow import get_workflow
        workflow = get_workflow()
        logger.info("✅ LangGraph workflow initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize workflow: {e}", exc_info=True)

    # Start session cleanup background task
    cleanup_task = asyncio.create_task(session_cleanup_task())
    logger.info("✅ Session cleanup task started")

    logger.info(f"✅ {settings.APP_NAME} started successfully")

    yield

    # Shutdown
    logger.info(f"👋 Shutting down {settings.APP_NAME}")

    # Cancel cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("✅ Session cleanup task stopped")
        except Exception as e:
            logger.error(f"Error stopping cleanup task: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready multi-agent insurance support system",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

# CORS Middleware
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    logger.info("✅ CORS middleware enabled")


# Request ID Middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Add to logger context
    logger.info(
        f"→ {request.method} {request.url.path}",
        extra={"request_id": request_id},
    )

    start_time = time.time()

    try:
        response = await call_next(request)

        # Track metrics
        duration = time.time() - start_time
        metrics.api_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        metrics.api_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).inc()

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"← {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
            extra={"request_id": request_id, "duration_ms": duration * 1000},
        )

        return response

    except Exception as e:
        duration = time.time() - start_time

        logger.error(
            f"❌ {request.method} {request.url.path} - Error: {str(e)}",
            extra={"request_id": request_id},
            exc_info=True,
        )

        metrics.api_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,
        ).inc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                request_id=request_id,
            ).model_dump(),
            headers={"X-Request-ID": request_id},
        )


# Metrics Tracking Middleware
@app.middleware("http")
async def track_in_progress_requests(request: Request, call_next):
    """Track in-progress API requests."""
    metrics.api_requests_in_progress.labels(
        method=request.method,
        endpoint=request.url.path,
    ).inc()

    try:
        response = await call_next(request)
        return response
    finally:
        metrics.api_requests_in_progress.labels(
            method=request.method,
            endpoint=request.url.path,
        ).dec()


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(f"Validation error: {exc}", extra={"request_id": request_id})

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="Validation error",
            details=[{"message": str(exc), "type": "ValueError"}],
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"request_id": request_id},
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            details=[{"message": "An unexpected error occurred", "type": type(exc).__name__}],
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-ID": request_id},
    )


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/health",
    }


# ============================================================================
# Application Startup Message
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {settings.APP_NAME} on {settings.API_HOST}:{settings.API_PORT}")

    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        workers=settings.API_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
