"""
Billing-related tools for querying billing and payment information.
"""
import time
from typing import Dict, Any, List
from src.database.connection import connect_db
from src.observability.logging_config import get_logger
from src.observability.tracing import trace_function
from src.observability import metrics

logger = get_logger(__name__)


@trace_function(name="get_billing_info", attributes={"db.operation": "select", "db.table": "billing"})
def get_billing_info(policy_number: str = None, customer_id: str = None) -> Dict[str, Any]:
    """
    Get billing information including current balance and due dates.

    Args:
        policy_number: Policy number to lookup
        customer_id: Customer ID to lookup

    Returns:
        Dictionary containing billing information or error
    """
    logger.info(f"🔍 Fetching billing info - Policy: {policy_number}, Customer: {customer_id}")
    start_time = time.time()

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if policy_number:
            cursor.execute("""
                SELECT b.*, p.premium_amount, p.billing_frequency
                FROM billing b
                JOIN policies p ON b.policy_number = p.policy_number
                WHERE b.policy_number = ? AND b.status = 'pending'
                ORDER BY b.due_date DESC LIMIT 1
            """, (policy_number,))
        elif customer_id:
            cursor.execute("""
                SELECT b.*, p.premium_amount, p.billing_frequency
                FROM billing b
                JOIN policies p ON b.policy_number = p.policy_number
                WHERE p.customer_id = ? AND b.status = 'pending'
                ORDER BY b.due_date DESC LIMIT 1
            """, (customer_id,))
        else:
            conn.close()
            return {"error": "Either policy_number or customer_id must be provided"}

        result = cursor.fetchone()
        conn.close()

        duration = time.time() - start_time
        metrics.db_query_duration_seconds.labels(
            operation="select", table="billing"
        ).observe(duration)

        if result:
            logger.info("✅ Billing info found")
            metrics.db_queries_total.labels(
                operation="select", table="billing", status="success"
            ).inc()

            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        else:
            logger.warning("❌ Billing info not found")
            metrics.db_queries_total.labels(
                operation="select", table="billing", status="not_found"
            ).inc()
            return {"error": "Billing information not found"}

    except Exception as e:
        logger.error(f"Database error fetching billing info: {e}", exc_info=True)
        metrics.db_queries_total.labels(
            operation="select", table="billing", status="error"
        ).inc()
        return {"error": f"Database error: {str(e)}"}


@trace_function(name="get_payment_history", attributes={"db.operation": "select", "db.table": "payments"})
def get_payment_history(policy_number: str) -> List[Dict[str, Any]]:
    """
    Get payment history for a policy.

    Args:
        policy_number: Policy number to lookup

    Returns:
        List of payment records or empty list
    """
    logger.info(f"🔍 Fetching payment history for policy: {policy_number}")
    start_time = time.time()

    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.payment_date, p.amount, p.status, p.payment_method
            FROM payments p
            JOIN billing b ON p.bill_id = b.bill_id
            WHERE b.policy_number = ?
            ORDER BY p.payment_date DESC LIMIT 10
        """, (policy_number,))

        results = cursor.fetchall()
        conn.close()

        duration = time.time() - start_time
        metrics.db_query_duration_seconds.labels(
            operation="select", table="payments"
        ).observe(duration)

        if results:
            logger.info(f"✅ Found {len(results)} payment records")
            metrics.db_queries_total.labels(
                operation="select", table="payments", status="success"
            ).inc()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        else:
            logger.warning("❌ No payment history found")
            metrics.db_queries_total.labels(
                operation="select", table="payments", status="not_found"
            ).inc()
            return []

    except Exception as e:
        logger.error(f"Database error fetching payment history: {e}", exc_info=True)
        metrics.db_queries_total.labels(
            operation="select", table="payments", status="error"
        ).inc()
        return []
