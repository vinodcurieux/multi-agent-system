"""
Human escalation agent for handling requests that require human intervention.
"""
from src.agents.base import BaseAgent
from src.agents.prompts import HUMAN_ESCALATION_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client


class HumanEscalationAgent(BaseAgent):
    """
    Human escalation agent.

    Handles:
    - Explicit requests to speak with a human
    - Complex issues beyond agent capabilities
    - Supervisor loop limit escalations
    """

    def __init__(self):
        super().__init__("human_escalation_agent")
        self.llm_client = get_llm_client()

    def process(self, state: GraphState) -> GraphState:
        """
        Process escalation to human representative.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with escalation response
        """
        self.logger.warning(
            f"🚨 Escalation triggered - State summary: "
            f"customer={state.get('customer_id')}, "
            f"policy={state.get('policy_number')}, "
            f"iterations={state.get('n_iteration')}"
        )

        # Prepare prompt
        prompt = HUMAN_ESCALATION_PROMPT.format(
            task=state.get("task", "Handle escalation request"),
            conversation_history=self.get_conversation_history(state),
        )

        # Generate escalation response
        self.logger.info("🤖 Generating escalation response...")
        response = self.llm_client.run_llm(prompt)

        self.logger.info("🚨 Conversation escalated to human")

        # Update state
        return {
            **state,
            "final_answer": response,
            "requires_human_escalation": True,
            "escalation_reason": state.get(
                "escalation_reason", "Customer requested human assistance."
            ),
            "messages": [("assistant", response)],
        }


def human_escalation_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = HumanEscalationAgent()
    return agent(state)
