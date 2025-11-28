"""
Session management endpoints.
Provides CRUD operations for conversation sessions.
"""
from fastapi import APIRouter, HTTPException, status, Request
from typing import List

from src.api.models import SessionResponse, SessionListResponse, ConversationMessage
from src.session.manager import get_session_manager
from src.session.models import MessageRole
from src.observability.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 100,
    http_request: Request = None,
):
    """
    List all active sessions.

    Args:
        limit: Maximum number of sessions to return (default: 100, max: 1000)
        http_request: FastAPI request object

    Returns:
        List of session summaries
    """
    request_id = getattr(http_request.state, "request_id", "unknown") if http_request else "unknown"

    # Validate limit
    if limit > 1000:
        limit = 1000

    logger.info(f"Listing sessions (limit={limit})", extra={"request_id": request_id})

    session_manager = get_session_manager()
    session_ids = session_manager.list_sessions(limit=limit)

    # Get full session data for each ID
    sessions = []
    for session_id in session_ids:
        session_state = session_manager.get_session(session_id)
        if session_state:
            # Convert to API response format
            messages = [
                ConversationMessage(
                    role=msg.role.value,
                    content=msg.content,
                    timestamp=msg.timestamp,
                )
                for msg in session_state.messages
            ]

            session_response = SessionResponse(
                session_id=session_state.session_id,
                created_at=session_state.created_at,
                last_activity=session_state.last_activity,
                messages=messages,
                state=session_state.context.model_dump(exclude_none=True),
            )
            sessions.append(session_response)

    logger.info(f"Found {len(sessions)} sessions", extra={"request_id": request_id})

    return SessionListResponse(
        sessions=sessions,
        total=len(sessions),
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    http_request: Request = None,
):
    """
    Get a specific session by ID.

    Args:
        session_id: Session identifier
        http_request: FastAPI request object

    Returns:
        Session details with full conversation history

    Raises:
        HTTPException: 404 if session not found
    """
    request_id = getattr(http_request.state, "request_id", "unknown") if http_request else "unknown"

    logger.info(f"Getting session: {session_id}", extra={"request_id": request_id, "session_id": session_id})

    session_manager = get_session_manager()
    session_state = session_manager.get_session(session_id)

    if not session_state:
        logger.warning(f"Session not found: {session_id}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Convert to API response format
    messages = [
        ConversationMessage(
            role=msg.role.value,
            content=msg.content,
            timestamp=msg.timestamp,
        )
        for msg in session_state.messages
    ]

    return SessionResponse(
        session_id=session_state.session_id,
        created_at=session_state.created_at,
        last_activity=session_state.last_activity,
        messages=messages,
        state=session_state.context.model_dump(exclude_none=True),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    http_request: Request = None,
):
    """
    Delete a session.

    Args:
        session_id: Session identifier
        http_request: FastAPI request object

    Returns:
        Success message

    Raises:
        HTTPException: 404 if session not found
    """
    request_id = getattr(http_request.state, "request_id", "unknown") if http_request else "unknown"

    logger.info(f"Deleting session: {session_id}", extra={"request_id": request_id, "session_id": session_id})

    session_manager = get_session_manager()
    deleted = session_manager.delete_session(session_id)

    if not deleted:
        logger.warning(f"Session not found for deletion: {session_id}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    logger.info(f"✅ Session deleted: {session_id}", extra={"request_id": request_id})

    return {
        "message": f"Session '{session_id}' deleted successfully",
        "session_id": session_id,
    }


@router.post("/sessions/{session_id}/refresh")
async def refresh_session(
    session_id: str,
    http_request: Request = None,
):
    """
    Refresh session TTL (extend expiration).

    Args:
        session_id: Session identifier
        http_request: FastAPI request object

    Returns:
        Success message with new expiration time

    Raises:
        HTTPException: 404 if session not found
    """
    request_id = getattr(http_request.state, "request_id", "unknown") if http_request else "unknown"

    logger.info(f"Refreshing session TTL: {session_id}", extra={"request_id": request_id, "session_id": session_id})

    session_manager = get_session_manager()
    refreshed = session_manager.refresh_ttl(session_id)

    if not refreshed:
        logger.warning(f"Session not found for refresh: {session_id}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Get updated session
    session_state = session_manager.get_session(session_id)

    logger.info(f"✅ Session TTL refreshed: {session_id}", extra={"request_id": request_id})

    return {
        "message": f"Session '{session_id}' TTL refreshed",
        "session_id": session_id,
        "expires_at": session_state.expires_at if session_state else None,
    }


@router.get("/sessions/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    http_request: Request = None,
):
    """
    Get session summary without full conversation history.

    Useful for dashboards and overview pages.

    Args:
        session_id: Session identifier
        http_request: FastAPI request object

    Returns:
        Session summary with metadata

    Raises:
        HTTPException: 404 if session not found
    """
    request_id = getattr(http_request.state, "request_id", "unknown") if http_request else "unknown"

    logger.debug(f"Getting session summary: {session_id}", extra={"request_id": request_id})

    session_manager = get_session_manager()
    session_state = session_manager.get_session(session_id)

    if not session_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    return session_state.get_summary()
