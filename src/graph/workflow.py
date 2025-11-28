"""
LangGraph workflow construction.
Builds and compiles the multi-agent workflow graph.
"""
from langgraph.graph import StateGraph, END
from typing import Optional

from src.graph.state import GraphState
from src.graph.routing import decide_next_agent
from src.agents.supervisor import supervisor_agent_node
from src.agents.policy_agent import policy_agent_node
from src.agents.billing_agent import billing_agent_node
from src.agents.claims_agent import claims_agent_node
from src.agents.general_help_agent import general_help_agent_node
from src.agents.human_escalation import human_escalation_node
from src.agents.final_answer import final_answer_agent_node
from src.observability.logging_config import get_logger

logger = get_logger(__name__)


def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow with all agents and routing logic.

    Returns:
        Compiled LangGraph workflow
    """
    logger.info("🏗️ Building LangGraph workflow...")

    # Initialize the workflow with GraphState
    workflow = StateGraph(GraphState)

    # Add all agent nodes
    workflow.add_node("supervisor_agent", supervisor_agent_node)
    workflow.add_node("policy_agent", policy_agent_node)
    workflow.add_node("billing_agent", billing_agent_node)
    workflow.add_node("claims_agent", claims_agent_node)
    workflow.add_node("general_help_agent", general_help_agent_node)
    workflow.add_node("human_escalation_agent", human_escalation_node)
    workflow.add_node("final_answer_agent", final_answer_agent_node)

    logger.info("✅ Added all agent nodes")

    # Set entry point
    workflow.set_entry_point("supervisor_agent")
    logger.info("✅ Set entry point: supervisor_agent")

    # Add conditional edges from supervisor to all possible agents
    workflow.add_conditional_edges(
        "supervisor_agent",
        decide_next_agent,
        {
            "supervisor_agent": "supervisor_agent",
            "policy_agent": "policy_agent",
            "billing_agent": "billing_agent",
            "claims_agent": "claims_agent",
            "human_escalation_agent": "human_escalation_agent",
            "general_help_agent": "general_help_agent",
            "end": "final_answer_agent",
        },
    )
    logger.info("✅ Added conditional edges from supervisor")

    # Return to supervisor after each specialist agent
    for agent in ["policy_agent", "billing_agent", "claims_agent", "general_help_agent"]:
        workflow.add_edge(agent, "supervisor_agent")
        logger.debug(f"✅ Added edge: {agent} → supervisor_agent")

    # Final answer agent leads to END
    workflow.add_edge("final_answer_agent", END)
    logger.info("✅ Added edge: final_answer_agent → END")

    # Human escalation leads to END
    workflow.add_edge("human_escalation_agent", END)
    logger.info("✅ Added edge: human_escalation_agent → END")

    logger.info("🎉 Workflow construction complete")

    return workflow


def compile_workflow(workflow: Optional[StateGraph] = None):
    """
    Compile the LangGraph workflow for execution.

    Args:
        workflow: Pre-built workflow (if None, creates new one)

    Returns:
        Compiled workflow ready for execution
    """
    if workflow is None:
        workflow = create_workflow()

    logger.info("⚙️ Compiling workflow...")
    compiled = workflow.compile()
    logger.info("✅ Workflow compiled successfully")

    return compiled


# Global compiled workflow instance
_compiled_workflow = None


def get_workflow():
    """
    Get the global compiled workflow instance.

    Returns:
        Compiled LangGraph workflow
    """
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = compile_workflow()
    return _compiled_workflow


def visualize_workflow(workflow=None, output_path: str = "workflow_graph.png"):
    """
    Generate a visual representation of the workflow.

    Args:
        workflow: Workflow to visualize (if None, uses global)
        output_path: Path to save the image

    Returns:
        PNG image bytes
    """
    if workflow is None:
        workflow = get_workflow()

    try:
        from IPython.display import Image

        graph_image = workflow.get_graph().draw_mermaid_png()

        # Save to file if path provided
        if output_path:
            with open(output_path, "wb") as f:
                f.write(graph_image)
            logger.info(f"✅ Workflow visualization saved to: {output_path}")

        return graph_image
    except ImportError:
        logger.warning(
            "IPython not available. Install with: pip install ipython"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to visualize workflow: {e}", exc_info=True)
        return None
