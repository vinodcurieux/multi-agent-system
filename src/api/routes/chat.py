"""
Chat endpoints for multi-agent conversation.
"""
from fastapi import APIRouter, HTTPException, status, Request
from typing import Optional
import uuid
import time

from src.api.models import ChatRequest, ChatResponse
from src.graph.workflow import get_workflow
from src.graph.state import create_initial_state
from src.session.manager import get_session_manager
from src.session.models import MessageRole
from src.observability.logging_config import get_logger
from src.observability import metrics
from src.config import settings

logger = get_logger(__name__)
router = APIRouter()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess_{uuid.uuid4().hex[:16]}"


def extract_agent_name(state: dict) -> Optional[str]:
    """Extract the last agent that processed the request."""
    # Check for next_agent (where supervisor routed to)
    if state.get("next_agent") and state["next_agent"] not in ["end", "supervisor_agent"]:
        return state["next_agent"]

    # Check messages for agent name
    messages = state.get("messages", [])
    if messages:
        # Try to infer from message metadata or content
        pass

    return "unknown"


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
):
    """
    Main chat endpoint for multi-agent conversation.

    Process user messages through the multi-agent system:
    1. Creates or retrieves session
    2. Builds graph state with user input and context
    3. Executes LangGraph workflow
    4. Returns agent response

    Args:
        request: Chat request with message and optional context
        http_request: FastAPI request object

    Returns:
        ChatResponse with agent's reply and metadata

    Raises:
        HTTPException: On workflow execution errors
    """
    request_id = getattr(http_request.state, "request_id", "unknown")

    # Generate or use provided session ID
    session_id = request.session_id or generate_session_id()

    logger.info(
        f"Chat request: session={session_id}, message='{request.message[:50]}...'",
        extra={"request_id": request_id, "session_id": session_id},
    )

    start_time = time.time()

    try:
        # Get session manager
        session_manager = get_session_manager()

        # Get or create session
        session = session_manager.get_or_create(session_id)
        logger.debug(
            f"Session retrieved: {len(session.messages)} existing messages",
            extra={"request_id": request_id, "session_id": session_id},
        )

        # Add user message to session
        session.add_message(
            role=MessageRole.USER,
            content=request.message,
            metadata={"request_id": request_id}
        )

        # Update context from request if provided
        if request.context:
            session.update_context(**request.context)

        # Get workflow
        workflow = get_workflow()

        # Create initial state from session
        initial_state = create_initial_state(
            user_input=request.message,
            session_id=session_id,
            customer_id=session.context.customer_id or request.context.get("customer_id"),
            policy_number=session.context.policy_number or request.context.get("policy_number"),
            claim_id=session.context.claim_id or request.context.get("claim_id"),
        )

        # If we have conversation history, include it
        if session.messages:
            initial_state["conversation_history"] = session.get_conversation_history()

        logger.debug(
            f"Initial state created with {len(session.messages)} messages",
            extra={"request_id": request_id, "session_id": session_id},
        )

        # Execute workflow
        logger.info(
            "Executing workflow...",
            extra={"request_id": request_id, "session_id": session_id},
        )

        result = workflow.invoke(initial_state)

        # Track conversation metrics
        duration = time.time() - start_time
        metrics.conversation_duration_seconds.observe(duration)
        metrics.conversations_total.labels(
            status="completed" if result.get("end_conversation") else "in_progress"
        ).inc()

        if result.get("n_iteration"):
            metrics.supervisor_iterations_total.observe(result["n_iteration"])

        # Extract response
        final_answer = result.get("final_answer", "")
        agent_used = extract_agent_name(result)
        requires_clarification = result.get("needs_clarification", False)
        conversation_complete = result.get("end_conversation", False) or result.get("requires_human_escalation", False)

        # If no final answer but have messages, extract last message
        if not final_answer and result.get("messages"):
            messages = result["messages"]
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, tuple) and len(last_msg) >= 2:
                    final_answer = last_msg[1]
                elif hasattr(last_msg, "content"):
                    final_answer = last_msg.content

        # Build metadata
        metadata = {
            "iterations": result.get("n_iteration", 0),
            "processing_time_ms": duration * 1000,
            "escalated": result.get("requires_human_escalation", False),
        }

        if result.get("escalation_reason"):
            metadata["escalation_reason"] = result["escalation_reason"]

        # Add assistant message to session
        session.add_message(
            role=MessageRole.ASSISTANT,
            content=final_answer or "I apologize, but I couldn't generate a response. Please try again.",
            metadata={
                "agent": agent_used,
                "iterations": result.get("n_iteration", 0),
                "request_id": request_id,
            }
        )

        # Update session context from workflow results
        if result.get("customer_id"):
            session.context.customer_id = result["customer_id"]
        if result.get("policy_number"):
            session.context.policy_number = result["policy_number"]
        if result.get("claim_id"):
            session.context.claim_id = result["claim_id"]

        # Update session metadata
        if agent_used and agent_used not in session.metadata.agents_used:
            session.metadata.agents_used.append(agent_used)

        session.metadata.total_iterations += result.get("n_iteration", 0)

        if result.get("requires_human_escalation"):
            session.metadata.escalated = True
            session.metadata.escalation_reason = result.get("escalation_reason")

        # Mark conversation as complete if needed
        if conversation_complete:
            session.mark_complete()

        # Store updated graph state for potential continuation
        session.graph_state = {
            "n_iteration": result.get("n_iteration", 0),
            "end_conversation": conversation_complete,
            "next_agent": result.get("next_agent"),
        }

        # Save session
        session_manager.update_session(session)

        # Update response metadata with session info
        metadata["total_messages"] = len(session.messages)
        metadata["total_iterations"] = session.metadata.total_iterations

        logger.info(
            f"Chat completed: agent={agent_used}, iterations={metadata['iterations']}, "
            f"duration={duration:.2f}s",
            extra={"request_id": request_id, "session_id": session_id},
        )

        response = ChatResponse(
            session_id=session_id,
            message=final_answer or "I apologize, but I couldn't generate a response. Please try again.",
            agent_used=agent_used,
            requires_clarification=requires_clarification,
            conversation_complete=conversation_complete,
            metadata=metadata,
        )

        # Track metrics
        metrics.conversation_turns_total.inc()

        return response

    except Exception as e:
        duration = time.time() - start_time
        metrics.conversations_total.labels(status="error").inc()

        logger.error(
            f"Chat error: {str(e)}",
            extra={"request_id": request_id, "session_id": session_id},
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to process chat request",
                "message": str(e),
                "request_id": request_id,
            },
        )


@router.get("/chat/test")
async def test_chat():
    """
    Simple test endpoint to verify chat API is working.

    Returns a test response without executing the workflow.
    """
    return {
        "status": "operational",
        "message": "Chat API is ready",
        "workflow_available": True,
    }
