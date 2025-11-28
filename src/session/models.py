"""
Session state models for conversation management.
Defines how session data is stored and retrieved.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    """Single message in a conversation."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionMetadata(BaseModel):
    """Session metadata for tracking and analytics."""

    total_messages: int = Field(default=0, description="Total messages in conversation")
    total_iterations: int = Field(default=0, description="Total supervisor iterations")
    agents_used: List[str] = Field(default_factory=list, description="List of agents used")
    escalated: bool = Field(default=False, description="Whether conversation was escalated")
    escalation_reason: Optional[str] = Field(default=None, description="Reason for escalation")
    total_tokens: int = Field(default=0, description="Total LLM tokens used")


class SessionContext(BaseModel):
    """Context extracted from conversation."""

    customer_id: Optional[str] = Field(default=None, description="Customer identifier")
    policy_number: Optional[str] = Field(default=None, description="Policy number")
    claim_id: Optional[str] = Field(default=None, description="Claim identifier")
    user_intent: Optional[str] = Field(default=None, description="Detected user intent")

    # Additional extracted entities
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")


class SessionState(BaseModel):
    """
    Complete session state stored in Redis.

    This represents a full conversation session including:
    - Session metadata
    - Conversation messages
    - Extracted context
    - Graph state (for workflow continuation)
    """

    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Session expiration time")

    # Conversation data
    messages: List[ConversationMessage] = Field(default_factory=list, description="Conversation messages")
    context: SessionContext = Field(default_factory=SessionContext, description="Session context")
    metadata: SessionMetadata = Field(default_factory=SessionMetadata, description="Session metadata")

    # Graph state for workflow continuation
    graph_state: Dict[str, Any] = Field(default_factory=dict, description="LangGraph state")

    # Status
    is_active: bool = Field(default=True, description="Whether session is active")
    conversation_complete: bool = Field(default=False, description="Whether conversation is complete")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the conversation.

        Args:
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata
        """
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.metadata.total_messages = len(self.messages)
        self.last_activity = datetime.utcnow()

    def update_context(self, **kwargs) -> None:
        """
        Update session context.

        Args:
            **kwargs: Context fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key) and value is not None:
                setattr(self.context, key, value)
        self.last_activity = datetime.utcnow()

    def mark_complete(self) -> None:
        """Mark the conversation as complete."""
        self.conversation_complete = True
        self.is_active = False
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create SessionState from dictionary."""
        # Convert string timestamps back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if 'last_activity' in data and isinstance(data['last_activity'], str):
            data['last_activity'] = datetime.fromisoformat(data['last_activity'].replace('Z', '+00:00'))
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))

        # Convert message timestamps
        if 'messages' in data:
            for msg in data['messages']:
                if 'timestamp' in msg and isinstance(msg['timestamp'], str):
                    msg['timestamp'] = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))

        return cls(**data)

    def get_conversation_history(self) -> str:
        """
        Get conversation history as formatted string.

        Returns:
            Formatted conversation history
        """
        history = []
        for msg in self.messages:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            history.append(f"{role}: {msg.content}")
        return "\n".join(history)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get session summary for API responses.

        Returns:
            Session summary dictionary
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "message_count": len(self.messages),
            "is_active": self.is_active,
            "conversation_complete": self.conversation_complete,
            "context": self.context.model_dump(exclude_none=True),
            "metadata": self.metadata.model_dump()
        }
