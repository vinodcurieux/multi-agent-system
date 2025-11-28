"""
Graph state definition for LangGraph workflow.
Defines the shared state that flows through all agents.
"""
from typing import TypedDict, List, Annotated, Dict, Any, Optional
from langgraph.graph import add_messages


class GraphState(TypedDict):
    """
    State that flows through the LangGraph workflow.

    This state is shared across all agents and contains:
    - Conversation tracking
    - Entity extraction
    - Routing decisions
    - Escalation flags
    - Metadata
    """

    # Core conversation tracking
    messages: Annotated[List[Any], add_messages]
    """List of messages in the conversation (managed by LangGraph)"""

    user_input: str
    """Current user input/query"""

    conversation_history: Optional[str]
    """Full conversation history as formatted string"""

    session_id: Optional[str]
    """Session identifier for stateful conversations"""

    # Iteration tracking
    n_iteration: Optional[int]
    """Number of supervisor iterations (for loop prevention)"""

    # Extracted context & metadata
    user_intent: Optional[str]
    """Detected user intent (e.g., 'query_policy', 'billing_issue')"""

    customer_id: Optional[str]
    """Customer identifier"""

    policy_number: Optional[str]
    """Policy number referenced in conversation"""

    claim_id: Optional[str]
    """Claim identifier if applicable"""

    # Supervisor / routing layer
    next_agent: Optional[str]
    """Next agent to route to"""

    task: Optional[str]
    """Current task determined by supervisor"""

    justification: Optional[str]
    """Supervisor's reasoning for routing decision"""

    end_conversation: Optional[bool]
    """Flag to indicate conversation should end"""

    # Clarification handling
    needs_clarification: Optional[bool]
    """Flag indicating supervisor needs user clarification"""

    clarification_question: Optional[str]
    """Question to ask user for clarification"""

    user_clarification: Optional[str]
    """User's response to clarification question"""

    # Entity extraction and DB lookups
    extracted_entities: Dict[str, Any]
    """Entities extracted from user input"""

    database_lookup_result: Dict[str, Any]
    """Results from database queries"""

    retrieved_faqs: Optional[List[Dict[str, Any]]]
    """FAQs retrieved from vector store"""

    # Escalation state
    requires_human_escalation: bool
    """Flag indicating need for human intervention"""

    escalation_reason: Optional[str]
    """Reason for escalation"""

    # Billing-specific fields
    billing_amount: Optional[float]
    """Billing amount if queried"""

    payment_method: Optional[str]
    """Payment method"""

    billing_frequency: Optional[str]
    """Billing frequency (monthly, quarterly, annual)"""

    invoice_date: Optional[str]
    """Invoice date"""

    # System-level metadata
    timestamp: Optional[str]
    """Timestamp of latest state update"""

    final_answer: Optional[str]
    """Final answer to present to user"""

    # Additional metadata
    metadata: Optional[Dict[str, Any]]
    """Additional metadata for tracking"""


def create_initial_state(
    user_input: str,
    session_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    policy_number: Optional[str] = None,
    **kwargs
) -> GraphState:
    """
    Create an initial graph state for a new conversation.

    Args:
        user_input: User's initial query
        session_id: Optional session identifier
        customer_id: Optional customer identifier from context
        policy_number: Optional policy number from context
        **kwargs: Additional state fields

    Returns:
        Initial GraphState
    """
    state: GraphState = {
        "messages": [],
        "user_input": user_input,
        "conversation_history": f"User: {user_input}",
        "session_id": session_id,
        "n_iteration": 0,
        "user_intent": None,
        "customer_id": customer_id,
        "policy_number": policy_number,
        "claim_id": None,
        "next_agent": "supervisor_agent",
        "task": "Help user with their query",
        "justification": None,
        "end_conversation": False,
        "needs_clarification": False,
        "clarification_question": None,
        "user_clarification": None,
        "extracted_entities": {},
        "database_lookup_result": {},
        "retrieved_faqs": None,
        "requires_human_escalation": False,
        "escalation_reason": None,
        "billing_amount": None,
        "payment_method": None,
        "billing_frequency": None,
        "invoice_date": None,
        "timestamp": None,
        "final_answer": None,
        "metadata": {},
    }

    # Update with any additional kwargs
    state.update(kwargs)

    return state


def update_state(state: GraphState, **updates) -> GraphState:
    """
    Update graph state with new values.

    Args:
        state: Current graph state
        **updates: Fields to update

    Returns:
        Updated graph state
    """
    state.update(updates)
    return state


def clear_clarification_state(state: GraphState) -> GraphState:
    """
    Clear clarification-related fields from state.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    state["needs_clarification"] = False
    state["clarification_question"] = None
    state["user_clarification"] = None
    return state
