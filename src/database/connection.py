"""
Database connection management.

Currently supports SQLite for development.
Will be migrated to PostgreSQL for production.
"""
import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional
from pathlib import Path

from src.config import settings
from src.observability.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Database connection manager.

    Currently uses SQLite for development compatibility.
    TODO: Migrate to SQLAlchemy with PostgreSQL support.
    """

    def __init__(self, db_path: str = "insurance_support.db"):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        logger.info(f"Database manager initialized: {db_path}")

    def connect(self) -> sqlite3.Connection:
        """
        Get a database connection.

        Returns:
            SQLite connection
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row  # Enable dict-like access
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.

        Yields:
            Database connection
        """
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error, rolling back: {e}")
            raise
        finally:
            # Note: Not closing here to allow connection reuse
            pass

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for database cursors.

        Yields:
            Database cursor
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def connect_db(db_path: str = "insurance_support.db") -> sqlite3.Connection:
    """
    Create a database connection (legacy function for compatibility).

    Args:
        db_path: Path to database file

    Returns:
        SQLite connection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
