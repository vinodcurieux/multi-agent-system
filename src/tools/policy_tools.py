"""
Policy-related tools for querying policy information.
"""
import time
from typing import Dict, Any
from src.database.connection import connect_db
from src.observability.logging_config import get_logger
from src.observability.tracing import trace_function
from src.observability import metrics

logger = get_logger(__name__)


@trace_function(name="get_policy_details", attributes={"db.operation": "select", "db.table": "policies"})
def get_policy_details(policy_number: str) -> Dict[str, Any]:
    """
    Fetch a customer's policy details by policy number.

    Args:
        policy_number: Policy number to lookup

    Returns:
        Dictionary containing policy details or error
    """
    logger.info(f"🔍 Fetching policy details for: {policy_number}")
    start_time = time.time()

    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, c.first_name, c.last_name
            FROM policies p
            JOIN customers c ON p.customer_id = c.customer_id
            WHERE p.policy_number = ?
        """, (policy_number,))

        result = cursor.fetchone()
        conn.close()

        duration = time.time() - start_time
        metrics.db_query_duration_seconds.labels(
            operation="select", table="policies"
        ).observe(duration)

        if result:
            logger.info(f"✅ Policy found: {policy_number}")
            metrics.db_queries_total.labels(
                operation="select", table="policies", status="success"
            ).inc()

            # Convert Row object to dict
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        else:
            logger.warning(f"❌ Policy not found: {policy_number}")
            metrics.db_queries_total.labels(
                operation="select", table="policies", status="not_found"
            ).inc()
            return {"error": "Policy not found"}

    except Exception as e:
        logger.error(f"Database error fetching policy {policy_number}: {e}", exc_info=True)
        metrics.db_queries_total.labels(
            operation="select", table="policies", status="error"
        ).inc()
        return {"error": f"Database error: {str(e)}"}


@trace_function(name="get_auto_policy_details", attributes={"db.operation": "select", "db.table": "auto_policy_details"})
def get_auto_policy_details(policy_number: str) -> Dict[str, Any]:
    """
    Get auto-specific policy details including vehicle info and deductibles.

    Args:
        policy_number: Policy number to lookup

    Returns:
        Dictionary containing auto policy details or error
    """
    logger.info(f"🔍 Fetching auto policy details for: {policy_number}")
    start_time = time.time()

    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT apd.*, p.policy_type, p.premium_amount
            FROM auto_policy_details apd
            JOIN policies p ON apd.policy_number = p.policy_number
            WHERE apd.policy_number = ?
        """, (policy_number,))

        result = cursor.fetchone()
        conn.close()

        duration = time.time() - start_time
        metrics.db_query_duration_seconds.labels(
            operation="select", table="auto_policy_details"
        ).observe(duration)

        if result:
            logger.info("✅ Auto policy details found")
            metrics.db_queries_total.labels(
                operation="select", table="auto_policy_details", status="success"
            ).inc()

            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        else:
            logger.warning("❌ Auto policy details not found")
            metrics.db_queries_total.labels(
                operation="select", table="auto_policy_details", status="not_found"
            ).inc()
            return {"error": "Auto policy details not found"}

    except Exception as e:
        logger.error(f"Database error fetching auto policy {policy_number}: {e}", exc_info=True)
        metrics.db_queries_total.labels(
            operation="select", table="auto_policy_details", status="error"
        ).inc()
        return {"error": f"Database error: {str(e)}"}
