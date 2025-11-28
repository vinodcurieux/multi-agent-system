"""
Final answer agent for generating clean, user-friendly summaries.
"""
from src.agents.base import BaseAgent
from src.agents.prompts import FINAL_ANSWER_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client


class FinalAnswerAgent(BaseAgent):
    """
    Final answer agent.

    Generates clean, concise, user-friendly final responses
    by summarizing specialist agent outputs.
    """

    def __init__(self):
        super().__init__("final_answer_agent")
        self.llm_client = get_llm_client()

    def process(self, state: GraphState) -> GraphState:
        """
        Generate final user-facing answer.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with final answer
        """
        self.logger.info("🎯 Final answer agent started")

        user_query = state["user_input"]
        conversation_history = self.get_conversation_history(state)

        # Extract the most recent specialist response
        recent_responses = []
        for msg in reversed(state.get("messages", [])):
            # Handle different message formats
            if isinstance(msg, tuple) and len(msg) >= 2:
                role, content = msg[0], msg[1]
            elif hasattr(msg, "content"):
                content = msg.content
            else:
                continue

            # Skip clarification messages
            if isinstance(content, str) and "clarification" not in content.lower():
                recent_responses.append(content)
                if len(recent_responses) >= 2:
                    break

        specialist_response = (
            recent_responses[0] if recent_responses else "No response available"
        )

        # Generate final answer
        prompt = FINAL_ANSWER_PROMPT.format(
            specialist_response=specialist_response,
            user_query=user_query,
        )

        self.logger.info("🤖 Generating final summary...")
        final_answer = self.llm_client.run_llm(prompt)

        self.logger.info(f"✅ Final answer generated: {final_answer[:100]}...")

        # Update state with clean final answer
        state["final_answer"] = final_answer
        state["end_conversation"] = True
        state["conversation_history"] = f"{conversation_history}\nAssistant: {final_answer}"
        state["messages"] = [("assistant", final_answer)]

        return state


def final_answer_agent_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = FinalAnswerAgent()
    return agent(state)
