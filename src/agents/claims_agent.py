"""
Claims specialist agent for handling claim-related queries.
"""
from src.agents.base import BaseAgent
from src.agents.prompts import CLAIMS_AGENT_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client
from src.tools.claims_tools import get_claim_status


class ClaimsAgent(BaseAgent):
    """
    Claims specialist agent.

    Handles queries about:
    - Claim status
    - Claim filing
    - Claim settlements
    - Incident types
    """

    def __init__(self):
        super().__init__("claims_agent")
        self.llm_client = get_llm_client()

    def process(self, state: GraphState) -> GraphState:
        """
        Process claims-related queries.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with claim information
        """
        self.log_state_info(state)

        # Prepare prompt
        prompt = CLAIMS_AGENT_PROMPT.format(
            task=state.get("task", "Assist with claim query"),
            policy_number=state.get("policy_number", "Not provided"),
            claim_id=state.get("claim_id", "Not provided"),
            conversation_history=self.get_conversation_history(state),
        )

        # Define tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_claim_status",
                    "description": "Retrieve claim details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "claim_id": {"type": "string"},
                            "policy_number": {"type": "string"},
                        },
                    },
                },
            }
        ]

        # Execute with LLM
        self.logger.info("🔄 Processing claims request...")
        result = self.llm_client.run_llm(
            prompt,
            tools=tools,
            tool_functions={"get_claim_status": get_claim_status},
        )

        self.logger.info("✅ Claims agent completed")

        # Update state with response
        return self.add_message(state, "assistant", result)


def claims_agent_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = ClaimsAgent()
    return agent(state)
