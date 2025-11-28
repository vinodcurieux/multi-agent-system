"""
Supervisor agent for routing requests to specialist agents.
"""
import json
from typing import Dict, Any

from src.agents.base import BaseAgent
from src.agents.prompts import SUPERVISOR_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client
from src.tools.user_interaction import ask_user
from src.config import settings


class SupervisorAgent(BaseAgent):
    """
    Supervisor agent that routes requests to appropriate specialist agents.

    Responsibilities:
    - Understand user intent
    - Determine if clarification is needed
    - Route to appropriate specialist agent
    - Prevent infinite loops
    - Escalate when necessary
    """

    def __init__(self):
        super().__init__("supervisor_agent")
        self.llm_client = get_llm_client()
        self.max_iterations = settings.SUPERVISOR_MAX_ITERATIONS

    def process(self, state: GraphState) -> GraphState:
        """
        Process the state and determine routing.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with routing decision
        """
        # Increment iteration counter
        n_iter = state.get("n_iteration", 0) + 1
        state["n_iteration"] = n_iter
        self.logger.info(f"🔢 Supervisor iteration: {n_iter}")

        # Force escalation if iteration limit reached
        if n_iter >= self.max_iterations:
            self.logger.warning(
                f"⚠️ Maximum supervisor iterations ({self.max_iterations}) reached — escalating to human agent"
            )
            updated_history = (
                state.get("conversation_history", "")
                + "\nAssistant: It seems this issue requires human review. Escalating to a human support specialist."
            )
            return {
                **state,
                "escalate_to_human": True,
                "conversation_history": updated_history,
                "next_agent": "human_escalation_agent",
                "n_iteration": n_iter,
            }

        # Check if we're coming from a clarification
        if state.get("needs_clarification", False):
            return self._handle_clarification(state, n_iter)

        # Normal routing logic
        return self._route_request(state, n_iter)

    def _handle_clarification(self, state: GraphState, n_iter: int) -> GraphState:
        """
        Handle returning from a clarification request.

        Args:
            state: Current graph state
            n_iter: Current iteration number

        Returns:
            Updated state with clarification processed
        """
        user_clarification = state.get("user_clarification", "")
        self.logger.info(f"🔄 Processing user clarification: {user_clarification}")

        # Update conversation history with the clarification exchange
        clarification_question = state.get("clarification_question", "")
        updated_conversation = (
            state.get("conversation_history", "")
            + f"\nAssistant: {clarification_question}\nUser: {user_clarification}"
        )

        # Clear clarification flags and update history
        updated_state = {
            **state,
            "needs_clarification": False,
            "conversation_history": updated_conversation,
            "n_iteration": n_iter,
        }

        # Remove clarification fields
        updated_state.pop("clarification_question", None)
        updated_state.pop("user_clarification", None)

        return updated_state

    def _route_request(self, state: GraphState, n_iter: int) -> GraphState:
        """
        Route the request to appropriate agent.

        Args:
            state: Current graph state
            n_iter: Current iteration number

        Returns:
            Updated state with routing decision
        """
        conversation_history = state.get("conversation_history", "")
        full_context = f"Full Conversation:\n{conversation_history}"

        prompt = SUPERVISOR_PROMPT.format(conversation_history=full_context)

        # Define ask_user tool
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Ask the user for clarification or additional information when their query is unclear or missing important details. ONLY use this if essential information like policy number or customer ID is missing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The specific question to ask the user for clarification",
                            },
                            "missing_info": {
                                "type": "string",
                                "description": "What specific information is missing or needs clarification",
                            },
                        },
                        "required": ["question", "missing_info"],
                    },
                },
            }
        ]

        self.logger.debug("🤖 Calling LLM for supervisor decision...")

        # Make LLM request with tool support
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Check if supervisor wants to ask user for clarification
        if getattr(message, "tool_calls", None):
            self.logger.info("🛠️ Supervisor requesting user clarification")
            for tool_call in message.tool_calls:
                if tool_call.function.name == "ask_user":
                    args = json.loads(tool_call.function.arguments)
                    question = args.get("question", "Can you please provide more details?")
                    missing_info = args.get("missing_info", "additional information")

                    self.logger.info(f"❓ Asking user: {question}")

                    # Get user response
                    user_response_data = ask_user(question, missing_info)
                    user_response = user_response_data["context"]

                    self.logger.info(f"✅ User response: {user_response}")

                    # Update conversation history
                    updated_history = conversation_history + f"\nAssistant: {question}"
                    updated_history = updated_history + f"\nUser: {user_response}"

                    return {
                        **state,
                        "needs_clarification": True,
                        "clarification_question": question,
                        "user_clarification": user_response,
                        "conversation_history": updated_history,
                        "n_iteration": n_iter,
                    }

        # Parse routing decision
        message_content = message.content

        try:
            parsed = json.loads(message_content)
            self.logger.info("✅ Supervisor output parsed successfully")
        except json.JSONDecodeError:
            self.logger.warning("❌ Supervisor output invalid JSON, using fallback")
            parsed = {}

        next_agent = parsed.get("next_agent", "general_help_agent")
        task = parsed.get("task", "Assist the user with their query.")
        justification = parsed.get("justification", "")

        self.logger.info(f"---SUPERVISOR DECISION: {next_agent}---")
        self.logger.info(f"Task: {task}")
        self.logger.info(f"Reason: {justification}")

        # Update conversation history
        updated_conversation = (
            conversation_history + f"\nAssistant: Routing to {next_agent} for: {task}"
        )

        self.logger.info(f"➡️ Routing to: {next_agent}")

        return {
            **state,
            "next_agent": next_agent,
            "task": task,
            "justification": justification,
            "conversation_history": updated_conversation,
            "n_iteration": n_iter,
        }


def supervisor_agent_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = SupervisorAgent()
    return agent(state)
