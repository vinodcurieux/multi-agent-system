"""
Routing logic for LangGraph workflow.
Determines which agent to execute next based on state.
"""
from src.graph.state import GraphState
from src.observability.logging_config import get_logger

logger = get_logger(__name__)


def decide_next_agent(state: GraphState) -> str:
    """
    Decide which agent should execute next based on current state.

    This function is used by LangGraph to determine the workflow path.

    Args:
        state: Current graph state

    Returns:
        Name of the next agent to execute or "end" to terminate
    """
    # Handle clarification case first
    if state.get("needs_clarification"):
        logger.info("🔄 Routing back to supervisor for clarification processing")
        return "supervisor_agent"

    # Check if conversation should end
    if state.get("end_conversation"):
        logger.info("🏁 Routing to end - conversation complete")
        return "end"

    # Check for human escalation
    if state.get("requires_human_escalation"):
        logger.info("🚨 Routing to human escalation agent")
        return "human_escalation_agent"

    # Get next agent from state
    next_agent = state.get("next_agent", "general_help_agent")

    logger.info(f"➡️ Routing to: {next_agent}")
    return next_agent


def should_end_conversation(state: GraphState) -> bool:
    """
    Determine if the conversation should end.

    Args:
        state: Current graph state

    Returns:
        True if conversation should end, False otherwise
    """
    return state.get("end_conversation", False) or state.get(
        "requires_human_escalation", False
    )
