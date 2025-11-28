"""
Base agent class for all specialist agents.
Provides common functionality and interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time

from src.graph.state import GraphState
from src.observability.tracing import trace_agent
from src.observability.logging_config import get_logger
from src.observability import metrics
from src.config import settings


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    All specialist agents should inherit from this class and implement
    the process() method.
    """

    def __init__(self, name: str):
        """
        Initialize the agent.

        Args:
            name: Agent name (used for logging and tracing)
        """
        self.name = name
        self.logger = get_logger(f"agent.{name}")
        self.settings = settings

    @trace_agent
    def __call__(self, state: GraphState) -> GraphState:
        """
        Execute the agent with tracing and metrics.

        Args:
            state: Current graph state

        Returns:
            Updated graph state
        """
        self.logger.info(f"--- {self.name.upper()} STARTED ---")

        start_time = time.time()

        try:
            # Process the state
            result = self.process(state)

            # Track metrics
            duration = time.time() - start_time
            metrics.agent_invocations_total.labels(
                agent_name=self.name, status="success"
            ).inc()
            metrics.agent_duration_seconds.labels(agent_name=self.name).observe(duration)

            self.logger.info(
                f"--- {self.name.upper()} COMPLETED --- (duration: {duration:.2f}s)"
            )

            return result

        except Exception as e:
            # Track error metrics
            metrics.agent_errors_total.labels(
                agent_name=self.name, error_type=type(e).__name__
            ).inc()
            metrics.agent_invocations_total.labels(
                agent_name=self.name, status="error"
            ).inc()

            self.logger.error(
                f"--- {self.name.upper()} FAILED --- Error: {str(e)}", exc_info=True
            )
            raise

    @abstractmethod
    def process(self, state: GraphState) -> GraphState:
        """
        Process the current state and return updated state.

        This method must be implemented by all subclasses.

        Args:
            state: Current graph state

        Returns:
            Updated graph state
        """
        pass

    def update_conversation_history(
        self, state: GraphState, message: str
    ) -> str:
        """
        Update conversation history with a new message.

        Args:
            state: Current graph state
            message: Message to add to history

        Returns:
            Updated conversation history
        """
        current_history = state.get("conversation_history", "")
        updated_history = f"{current_history}\n{self.name}: {message}".strip()
        return updated_history

    def get_task(self, state: GraphState) -> str:
        """
        Get the task assigned to this agent.

        Args:
            state: Current graph state

        Returns:
            Task description
        """
        return state.get("task", "No task assigned")

    def get_conversation_history(self, state: GraphState) -> str:
        """
        Get the conversation history from state.

        Args:
            state: Current graph state

        Returns:
            Conversation history
        """
        return state.get("conversation_history", "")

    def add_message(self, state: GraphState, role: str, content: str) -> GraphState:
        """
        Add a message to the state's messages list.

        Args:
            state: Current graph state
            role: Message role (e.g., "assistant", "user")
            content: Message content

        Returns:
            Updated state with new message
        """
        messages = state.get("messages", [])
        messages.append((role, content))
        state["messages"] = messages
        return state

    def log_state_info(self, state: GraphState) -> None:
        """
        Log relevant information from the state for debugging.

        Args:
            state: Current graph state
        """
        self.logger.debug(f"Task: {state.get('task', 'N/A')}")
        self.logger.debug(f"Customer ID: {state.get('customer_id', 'N/A')}")
        self.logger.debug(f"Policy Number: {state.get('policy_number', 'N/A')}")
        self.logger.debug(f"Claim ID: {state.get('claim_id', 'N/A')}")
        self.logger.debug(f"Iteration: {state.get('n_iteration', 0)}")
