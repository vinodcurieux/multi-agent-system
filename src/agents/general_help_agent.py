"""
General help agent for FAQ and general insurance questions.
Uses RAG (Retrieval-Augmented Generation) with ChromaDB.
"""
from src.agents.base import BaseAgent
from src.agents.prompts import GENERAL_HELP_PROMPT
from src.graph.state import GraphState
from src.utils.llm_client import get_llm_client
from src.rag.vector_store import get_vector_store


class GeneralHelpAgent(BaseAgent):
    """
    General help agent using RAG for FAQ retrieval.

    Handles:
    - General insurance questions
    - FAQ queries
    - Educational content
    """

    def __init__(self):
        super().__init__("general_help_agent")
        self.llm_client = get_llm_client()
        self.vector_store = get_vector_store()

    def process(self, state: GraphState) -> GraphState:
        """
        Process general help queries using RAG.

        Args:
            state: Current graph state

        Returns:
            Updated graph state with FAQ-based response
        """
        user_query = state.get("user_input", "")
        conversation_history = self.get_conversation_history(state)
        task = state.get("task", "General insurance support")

        # Step 1: Retrieve relevant FAQs from vector store
        self.logger.info("🔍 Retrieving FAQs from vector database...")
        try:
            results = self.vector_store.query(user_query, n_results=3)

            # Format FAQ context
            faq_context = self.vector_store.format_faq_context(results)

            if results and results.get("metadatas"):
                num_faqs = len(results["metadatas"][0])
                self.logger.info(f"📚 Found {num_faqs} relevant FAQs")
            else:
                self.logger.warning("❌ No relevant FAQs found")
                faq_context = "No relevant FAQs were found."

        except Exception as e:
            self.logger.error(f"Failed to retrieve FAQs: {e}", exc_info=True)
            faq_context = "Error retrieving FAQs from knowledge base."

        # Step 2: Generate response using LLM with FAQ context
        prompt = GENERAL_HELP_PROMPT.format(
            task=task,
            conversation_history=conversation_history,
            faq_context=faq_context,
        )

        self.logger.info("🤖 Generating response with FAQ context...")
        final_answer = self.llm_client.run_llm(prompt)

        self.logger.info("✅ General help agent completed")

        # Update state
        updated_state = self.add_message(state, "assistant", final_answer)
        updated_state["retrieved_faqs"] = results.get("metadatas", [])
        updated_state["conversation_history"] = (
            f"{conversation_history}\nGeneral Help Agent: {final_answer}"
        )

        return updated_state


def general_help_agent_node(state: GraphState) -> GraphState:
    """
    Node function for LangGraph workflow.

    Args:
        state: Current graph state

    Returns:
        Updated graph state
    """
    agent = GeneralHelpAgent()
    return agent(state)
