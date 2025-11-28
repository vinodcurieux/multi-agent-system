"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============================================================================
# Chat API Models
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message or query",
        examples=["What is my auto insurance premium?"],
    )

    session_id: Optional[str] = Field(
        None,
        description="Session ID for continuing a conversation (optional for new conversations)",
        examples=["sess_abc123xyz"],
    )

    context: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Additional context like customer_id, policy_number, etc.",
        examples=[{"policy_number": "POL000004", "customer_id": "CUST00001"}],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    session_id: str = Field(
        ...,
        description="Session identifier for this conversation",
    )

    message: str = Field(
        ...,
        description="Agent's response to the user",
    )

    agent_used: Optional[str] = Field(
        None,
        description="Name of the agent that handled the query",
    )

    requires_clarification: bool = Field(
        False,
        description="Whether the system needs additional information",
    )

    conversation_complete: bool = Field(
        False,
        description="Whether the conversation has ended",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the response",
    )


# ============================================================================
# Session API Models
# ============================================================================

class ConversationMessage(BaseModel):
    """Single message in a conversation."""

    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class SessionResponse(BaseModel):
    """Response model for session retrieval."""

    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    messages: List[ConversationMessage] = Field(
        default_factory=list,
        description="Conversation messages",
    )
    state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Session state (customer_id, policy_number, etc.)",
    )


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""

    sessions: List[SessionResponse] = Field(
        default_factory=list,
        description="List of active sessions",
    )
    total: int = Field(..., description="Total number of sessions")


# ============================================================================
# Health Check Models
# ============================================================================

class ServiceStatus(BaseModel):
    """Status of a service dependency."""

    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status (healthy, unhealthy, degraded)")
    details: Optional[str] = Field(None, description="Additional status details")
    response_time_ms: Optional[float] = Field(None, description="Service response time in ms")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: List[ServiceStatus] = Field(
        default_factory=list,
        description="Status of all service dependencies",
    )


# ============================================================================
# Error Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information."""

    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type")
    field: Optional[str] = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(
        None,
        description="Detailed error information",
    )
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


# ============================================================================
# Metrics Models
# ============================================================================

class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""

    metrics: str = Field(..., description="Prometheus-format metrics")
    content_type: str = Field(
        default="text/plain; version=0.0.4; charset=utf-8",
        description="Prometheus metrics content type",
    )
