"""
Claims-related tools for querying claim status and information.
"""
import time
from typing import Dict, Any, List
from src.database.connection import connect_db
from src.observability.logging_config import get_logger
from src.observability.tracing import trace_function
from src.observability import metrics

logger = get_logger(__name__)


@trace_function(name="get_claim_status", attributes={"db.operation": "select", "db.table": "claims"})
def get_claim_status(claim_id: str = None, policy_number: str = None) -> Dict[str, Any]:
    """
    Get claim status and details.

    Args:
        claim_id: Claim ID to lookup
        policy_number: Policy number to find claims for

    Returns:
        Dictionary or list containing claim information
    """
    logger.info(f"🔍 Fetching claim status - Claim ID: {claim_id}, Policy: {policy_number}")
    start_time = time.time()

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if claim_id:
            cursor.execute("""
                SELECT c.*, p.policy_type
                FROM claims c
                JOIN policies p ON c.policy_number = p.policy_number
                WHERE c.claim_id = ?
            """, (claim_id,))
            result = cursor.fetchone()

            duration = time.time() - start_time
            metrics.db_query_duration_seconds.labels(
                operation="select", table="claims"
            ).observe(duration)

            if result:
                logger.info(f"✅ Claim found: {claim_id}")
                metrics.db_queries_total.labels(
                    operation="select", table="claims", status="success"
                ).inc()

                columns = [desc[0] for desc in cursor.description]
                conn.close()
                return dict(zip(columns, result))

        elif policy_number:
            cursor.execute("""
                SELECT c.*, p.policy_type
                FROM claims c
                JOIN policies p ON c.policy_number = p.policy_number
                WHERE c.policy_number = ?
                ORDER BY c.claim_date DESC LIMIT 3
            """, (policy_number,))
            results = cursor.fetchall()

            duration = time.time() - start_time
            metrics.db_query_duration_seconds.labels(
                operation="select", table="claims"
            ).observe(duration)

            if results:
                logger.info(f"✅ Found {len(results)} claim(s)")
                metrics.db_queries_total.labels(
                    operation="select", table="claims", status="success"
                ).inc()

                columns = [desc[0] for desc in cursor.description]
                conn.close()
                return [dict(zip(columns, row)) for row in results]

        conn.close()

        logger.warning("❌ No claims found")
        metrics.db_queries_total.labels(
            operation="select", table="claims", status="not_found"
        ).inc()
        return {"error": "Claim not found"}

    except Exception as e:
        logger.error(f"Database error fetching claim status: {e}", exc_info=True)
        metrics.db_queries_total.labels(
            operation="select", table="claims", status="error"
        ).inc()
        return {"error": f"Database error: {str(e)}"}
