"""
Policy specialist agent for handling policy-related queries.
"""
from src.agents.base import BaseAgent
from src.agents.prompts import POLICY_AGENT_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client
from src.tools.policy_tools import get_policy_details, get_auto_policy_details


class PolicyAgent(BaseAgent):
    """
    Policy specialist agent.

    Handles queries about:
    - Policy details and coverage
    - Vehicle information
    - Deductibles
    - Policy endorsements
    """

    def __init__(self):
        super().__init__("policy_agent")
        self.llm_client = get_llm_client()

    def process(self, state: GraphState) -> GraphState:
        """
        Process policy-related queries.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with policy information
        """
        self.log_state_info(state)

        # Prepare prompt
        prompt = POLICY_AGENT_PROMPT.format(
            task=state.get("task", "Assist with policy query"),
            policy_number=state.get("policy_number", "Not provided"),
            customer_id=state.get("customer_id", "Not provided"),
            conversation_history=self.get_conversation_history(state),
        )

        # Define tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_policy_details",
                    "description": "Fetch policy info by policy number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "policy_number": {"type": "string"}
                        },
                        "required": ["policy_number"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_auto_policy_details",
                    "description": "Get auto policy details including vehicle info",
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
        self.logger.info("🔄 Processing policy request...")
        result = self.llm_client.run_llm(
            prompt,
            tools=tools,
            tool_functions={
                "get_policy_details": get_policy_details,
                "get_auto_policy_details": get_auto_policy_details,
            },
        )

        self.logger.info("✅ Policy agent completed")

        # Update state with response
        return self.add_message(state, "assistant", result)


def policy_agent_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = PolicyAgent()
    return agent(state)
