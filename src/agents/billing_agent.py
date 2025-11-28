"""
Billing specialist agent for handling billing and payment queries.
"""
from src.agents.base import BaseAgent
from src.agents.prompts import BILLING_AGENT_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client
from src.tools.billing_tools import get_billing_info, get_payment_history


class BillingAgent(BaseAgent):
    """
    Billing specialist agent.

    Handles queries about:
    - Billing statements
    - Payment history
    - Premium amounts
    - Due dates
    """

    def __init__(self):
        super().__init__("billing_agent")
        self.llm_client = get_llm_client()

    def process(self, state: GraphState) -> GraphState:
        """
        Process billing-related queries.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with billing information
        """
        self.logger.info(f"TASK: {state.get('task')}")
        self.logger.info(f"USER QUERY: {state.get('user_input')}")
        self.logger.info(f"CONVERSATION HISTORY: {self.get_conversation_history(state)}")

        # Prepare prompt
        prompt = BILLING_AGENT_PROMPT.format(
            task=state.get("task", "Assist with billing query"),
            conversation_history=self.get_conversation_history(state),
        )

        # Define tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_billing_info",
                    "description": "Retrieve billing information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "policy_number": {"type": "string"},
                            "customer_id": {"type": "string"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_payment_history",
                    "description": "Fetch recent payment history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "policy_number": {"type": "string"}
                        },
                        "required": ["policy_number"],
                    },
                },
            },
        ]

        # Execute with LLM
        self.logger.info("🔄 Processing billing request...")
        result = self.llm_client.run_llm(
            prompt,
            tools=tools,
            tool_functions={
                "get_billing_info": get_billing_info,
                "get_payment_history": get_payment_history,
            },
        )

        self.logger.info("✅ Billing agent completed")

        # Update state with response
        updated_state = self.add_message(state, "assistant", result)

        # Preserve policy/customer info if present
        if state.get("policy_number"):
            updated_state["policy_number"] = state["policy_number"]
        if state.get("customer_id"):
            updated_state["customer_id"] = state["customer_id"]

        # Update conversation history
        current_history = self.get_conversation_history(state)
        updated_state["conversation_history"] = f"{current_history}\nBilling Agent: {result}"

        return updated_state


def billing_agent_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = BillingAgent()
    return agent(state)
