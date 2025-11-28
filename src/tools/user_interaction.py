"""
User interaction tools for getting clarification.
"""
from typing import Dict, Any
from src.observability.logging_config import get_logger

logger = get_logger(__name__)


def ask_user(question: str, missing_info: str = "") -> Dict[str, Any]:
    """
    Ask the user for input and return the response.

    Note: In production API, this should trigger a clarification response
    rather than blocking for input. This function is primarily for
    testing and development.

    Args:
        question: The question to ask the user
        missing_info: Description of what information is missing

    Returns:
        Dictionary with context and source
    """
    logger.info(f"🗣️ Asking user for input: {question}")

    if missing_info:
        print(f"---USER INPUT REQUIRED---\nMissing information: {missing_info}")
    else:
        print(f"---USER INPUT REQUIRED---")

    # In production, this would not block but return a flag
    # indicating clarification is needed
    answer = input(f"{question}: ")

    return {"context": answer, "source": "User Input"}
