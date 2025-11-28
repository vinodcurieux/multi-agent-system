"""
Redis-based session manager for stateful conversations.
Handles session storage, retrieval, and lifecycle management.
"""
import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from redis import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.session.models import SessionState, MessageRole
from src.config import settings
from src.observability.logging_config import get_logger
from src.observability.tracing import trace_function
from src.observability import metrics

logger = get_logger(__name__)


class SessionManager:
    """
    Manages conversation sessions using Redis.

    Features:
    - Session creation and retrieval
    - Automatic TTL management
    - Session listing and cleanup
    - Metrics tracking
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        key_prefix: str = "session:",
    ):
        """
        Initialize session manager.

        Args:
            redis_url: Redis connection URL (defaults to settings)
            ttl_seconds: Session TTL in seconds (defaults to settings)
            key_prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.ttl_seconds = ttl_seconds or settings.SESSION_TTL_SECONDS
        self.key_prefix = key_prefix

        self._redis: Optional[Redis] = None
        self._redis_available = False

        # Try to connect to Redis
        try:
            self._connect()
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory fallback: {e}")
            self._in_memory_store: Dict[str, SessionState] = {}

    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._redis = Redis.from_url(
                self.redis_url,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )

            # Test connection
            self._redis.ping()
            self._redis_available = True
            logger.info(f"✅ Connected to Redis: {self.redis_url}")

        except (RedisError, RedisConnectionError) as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            self._redis_available = False
            self._in_memory_store: Dict[str, SessionState] = {}

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    @trace_function(name="session_create", attributes={"operation": "create"})
    def create_session(self, session_id: str) -> SessionState:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier

        Returns:
            New SessionState
        """
        logger.info(f"Creating new session: {session_id}")

        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

        session = SessionState(
            session_id=session_id,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=expires_at,
        )

        # Store session
        self._set_session(session)

        metrics.session_operations_total.labels(operation="create", status="success").inc()
        metrics.active_sessions_total.inc()

        logger.info(f"✅ Session created: {session_id}")

        return session

    @trace_function(name="session_get", attributes={"operation": "get"})
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve a session.

        Args:
            session_id: Session identifier

        Returns:
            SessionState if found, None otherwise
        """
        logger.debug(f"Retrieving session: {session_id}")

        try:
            if self._redis_available and self._redis:
                # Get from Redis
                key = self._get_key(session_id)
                data = self._redis.get(key)

                if data:
                    session = SessionState.from_dict(json.loads(data))
                    metrics.session_operations_total.labels(operation="get", status="success").inc()
                    logger.debug(f"✅ Session found in Redis: {session_id}")
                    return session
                else:
                    metrics.session_operations_total.labels(operation="get", status="not_found").inc()
                    logger.debug(f"❌ Session not found in Redis: {session_id}")
                    return None

            else:
                # Get from in-memory store
                session = self._in_memory_store.get(session_id)
                if session:
                    metrics.session_operations_total.labels(operation="get", status="success").inc()
                    logger.debug(f"✅ Session found in memory: {session_id}")
                else:
                    metrics.session_operations_total.labels(operation="get", status="not_found").inc()
                    logger.debug(f"❌ Session not found in memory: {session_id}")
                return session

        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}", exc_info=True)
            metrics.session_operations_total.labels(operation="get", status="error").inc()
            return None

    def _set_session(self, session: SessionState) -> None:
        """
        Store session in Redis or memory.

        Args:
            session: SessionState to store
        """
        try:
            if self._redis_available and self._redis:
                # Store in Redis with TTL
                key = self._get_key(session.session_id)
                data = json.dumps(session.to_dict())
                self._redis.setex(key, self.ttl_seconds, data)
            else:
                # Store in memory
                self._in_memory_store[session.session_id] = session

        except Exception as e:
            logger.error(f"Error storing session {session.session_id}: {e}", exc_info=True)
            # Fallback to memory
            self._in_memory_store[session.session_id] = session

    @trace_function(name="session_update", attributes={"operation": "update"})
    def update_session(self, session: SessionState) -> None:
        """
        Update an existing session.

        Args:
            session: SessionState to update
        """
        logger.debug(f"Updating session: {session.session_id}")

        session.last_activity = datetime.utcnow()
        self._set_session(session)

        metrics.session_operations_total.labels(operation="update", status="success").inc()

    @trace_function(name="session_delete", attributes={"operation": "delete"})
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting session: {session_id}")

        try:
            if self._redis_available and self._redis:
                key = self._get_key(session_id)
                deleted = self._redis.delete(key)

                if deleted:
                    metrics.session_operations_total.labels(operation="delete", status="success").inc()
                    metrics.active_sessions_total.dec()
                    logger.info(f"✅ Session deleted from Redis: {session_id}")
                    return True
                else:
                    metrics.session_operations_total.labels(operation="delete", status="not_found").inc()
                    return False

            else:
                # Delete from memory
                if session_id in self._in_memory_store:
                    del self._in_memory_store[session_id]
                    metrics.session_operations_total.labels(operation="delete", status="success").inc()
                    metrics.active_sessions_total.dec()
                    logger.info(f"✅ Session deleted from memory: {session_id}")
                    return True
                else:
                    metrics.session_operations_total.labels(operation="delete", status="not_found").inc()
                    return False

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            metrics.session_operations_total.labels(operation="delete", status="error").inc()
            return False

    def list_sessions(self, limit: int = 100) -> List[str]:
        """
        List all active sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session IDs
        """
        logger.debug(f"Listing sessions (limit={limit})")

        try:
            if self._redis_available and self._redis:
                # List from Redis
                pattern = f"{self.key_prefix}*"
                keys = self._redis.keys(pattern)
                session_ids = [key.replace(self.key_prefix, "") for key in keys[:limit]]
                logger.debug(f"Found {len(session_ids)} sessions in Redis")
                return session_ids

            else:
                # List from memory
                session_ids = list(self._in_memory_store.keys())[:limit]
                logger.debug(f"Found {len(session_ids)} sessions in memory")
                return session_ids

        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []

    def get_or_create(self, session_id: str) -> SessionState:
        """
        Get existing session or create new one.

        Args:
            session_id: Session identifier

        Returns:
            SessionState (existing or new)
        """
        session = self.get_session(session_id)

        if session is None:
            session = self.create_session(session_id)

        return session

    def refresh_ttl(self, session_id: str) -> bool:
        """
        Refresh session TTL (extend expiration).

        Args:
            session_id: Session identifier

        Returns:
            True if refreshed, False if not found
        """
        session = self.get_session(session_id)

        if session:
            session.expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
            self.update_session(session)
            logger.debug(f"✅ Session TTL refreshed: {session_id}")
            return True
        else:
            logger.warning(f"❌ Cannot refresh TTL, session not found: {session_id}")
            return False

    def cleanup_expired(self) -> int:
        """
        Clean up expired sessions (for in-memory store only).

        Redis handles expiration automatically.

        Returns:
            Number of sessions cleaned up
        """
        if self._redis_available:
            # Redis handles cleanup automatically
            return 0

        # Clean up in-memory store
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self._in_memory_store.items()
            if session.expires_at and session.expires_at < now
        ]

        for sid in expired:
            del self._in_memory_store[sid]
            metrics.active_sessions_total.dec()

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    Returns:
        SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
