import pandas as pd
import numpy as np
import json
import re
from typing import List, Dict, Any, Tuple, Optional
import time
from dotenv import load_dotenv
import openai
import os
from datasets import load_dataset
import chromadb
from datetime import datetime, timedelta
import random
import sqlite3
from openai import OpenAI
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.trace import get_current_span
from phoenix.otel import register

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated, Dict, Any, Optional
from langgraph.graph import add_messages
from datetime import datetime
from prompt_monitoring import create_trace_agent
from supervisor_agent import supervisor_agent
from policy_agent_node import policy_agent_node
from billing_agent_node import billing_agent_node
from claims_agent_node import claims_agent_node
from general_help_agent_node import general_help_agent_node
from human_escalation_node import human_escalation_node
from final_answer_agent import final_answer_agent

client = None

def run_llm(
    prompt: str,
    tools: Optional[List[Dict]] = None,
    tool_functions: Optional[Dict[str, Any]] = None,
    model: str = "gpt-5-mini",
) -> str:
    """
    Run an LLM request that optionally supports tools.
    
    Args:
        prompt (str): The system or user prompt to send.
        tools (list[dict], optional): Tool schema list for model function calling.
        tool_functions (dict[str, callable], optional): Mapping of tool names to Python functions.
        model (str): Model name to use (default: gpt-5-mini).

    Returns:
        str: Final LLM response text.
    """

    # Step 1: Initial LLM call
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        tools=tools if tools else None,
        tool_choice="auto" if tools else None
    )

    message = response.choices[0].message
    print("Initial LLM Response:", message)

    # Step 2: If no tools or no tool calls, return simple model response
    if not getattr(message, "tool_calls", None):
        return message.content

    # Step 3: Handle tool calls dynamically
    if not tool_functions:
        return message.content + "\n\n⚠️ No tool functions provided to execute tool calls."

    tool_messages = []
    for tool_call in message.tool_calls:
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")
        tool_fn = tool_functions.get(func_name)

        try:
            result = tool_fn(**args) if tool_fn else {"error": f"Tool '{func_name}' not implemented."}
        except Exception as e:
            result = {"error": str(e)}

        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })

    # Step 4: Second pass — send tool outputs back to the model
    followup_messages = [
        {"role": "system", "content": prompt},
        {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                } for tc in message.tool_calls
            ],
        },
        *tool_messages,
    ]

    final = client.chat.completions.create(model=model, messages=followup_messages)
    return final.choices[0].message.content

class GraphState(TypedDict):
    # Core conversation tracking
    messages: Annotated[List[Any], add_messages]
    user_input: str
    conversation_history: Optional[str]

    n_iteration: Optional[int]

    # Extracted context & metadata
    user_intent: Optional[str]            # e.g., "query_policy", "billing_issue"
    customer_id: Optional[str]
    policy_number: Optional[str]
    claim_id: Optional[str]
    
    # Supervisor / routing layer
    next_agent: Optional[str]             # e.g., "policy_agent", "claims_agent", etc.
    task: Optional[str]                   # Current task determined by supervisor
    justification: Optional[str]          # Supervisor reasoning/explanation
    end_conversation: Optional[bool]      # Flag for graceful conversation termination
    
    # Entity extraction and DB lookups
    extracted_entities: Dict[str, Any]    # Parsed from user input (dates, names, etc.)
    database_lookup_result: Dict[str, Any]
    
    # Escalation state
    requires_human_escalation: bool
    escalation_reason: Optional[str]
    
    # Billing-specific fields
    billing_amount: Optional[float]
    payment_method: Optional[str]
    billing_frequency: Optional[str]      # "monthly", "quarterly", "annual"
    invoice_date: Optional[str]
    
    # System-level metadata
    timestamp: Optional[str]     # Track time of latest user message or state update
    final_answer: Optional[str]

def decide_next_agent(state):
    # Handle clarification case first
    if state.get("needs_clarification"):
        return "supervisor_agent"  # Return to supervisor to process the clarification
    
    if state.get("end_conversation"):
        return "end"
    
    if state.get("requires_human_escalation"):
        return "human_escalation_agent"
    
    return state.get("next_agent", "general_help_agent")


def create_langgraph_app():
    # Update the workflow to include the final_answer_agent
    workflow = StateGraph(GraphState)

    workflow.add_node("supervisor_agent", supervisor_agent)
    workflow.add_node("policy_agent", policy_agent_node)
    workflow.add_node("billing_agent", billing_agent_node)
    workflow.add_node("claims_agent", claims_agent_node)
    workflow.add_node("general_help_agent", general_help_agent_node)
    workflow.add_node("human_escalation_agent", human_escalation_node)
    workflow.add_node("final_answer_agent", final_answer_agent)  # Add this

    workflow.set_entry_point("supervisor_agent")

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
            "end": "final_answer_agent"
        }
    )

    # Return to Supervisor after each specialist
    for node in ["policy_agent", "billing_agent", "claims_agent", "general_help_agent"]:
        workflow.add_edge(node, "supervisor_agent")

    # Final answer agent → END
    workflow.add_edge("final_answer_agent", END)

    # Human escalation → END
    workflow.add_edge("human_escalation_agent", END)

    return workflow.compile()

app = None

def init_app():
    # ✅ Load environment variables
    load_dotenv()
    openai_api_key = os.getenv("OPEN_AI_KEY")
    phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")

    print("openai_api_key", openai_api_key)
    print("phoenix_endpoint", phoenix_endpoint)

    # init OpenAI
    global client
    client = OpenAI(api_key=openai_api_key)

    # Create agents
    create_trace_agent(phoenix_endpoint)

    # Testing agent
    # prompt = "Explain the theory of relativity in simple terms in 30 words."
    # response = run_llm(prompt)
    # print(response)

    # Create app
    global app
    app = create_langgraph_app()

# === Display the Graph ===
# from IPython.display import Image, display
# display(Image(app.get_graph().draw_mermaid_png()))


def run_test_query(query):
    """Test the system with a billing query"""
    initial_state = {
        "n_iteraton":0,
        "messages": [],
        "user_input": query,
        "user_intent": "",
        "claim_id": "",
        "next_agent": "supervisor_agent",
        "extracted_entities": {},
        "database_lookup_result": {},
        "requires_human_escalation": False,
        "escalation_reason": "",
        "billing_amount": None,
        "payment_method": None,
        "billing_frequency": None,
        "invoice_date": None,
        "conversation_history": f"User: {query}", 
        "task": "Help user with their query",
        "final_answer": ""
    }
    
    print(f"\n{'='*50}")
    print(f"QUERY: {query}")
    print(f"\n{'='*50}")
    
    # Run the graph
    final_state = app.invoke(initial_state)
    
    # Print the response
    print("\n---FINAL RESPONSE---")
    final_answer = final_state.get("final_answer", "No final answer generated.")
    print(final_answer)

    return final_state

init_app()
# POL000004 , 
test_query = "What is the premium of my auto insurance policy?"
final_output =  run_test_query(test_query)
