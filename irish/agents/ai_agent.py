from ai_router import ask_ai, get_mode
from intent_classifier import classify_intent
from memory import get_recent_memory, add_memory


def handle(prompt):

    memory = get_recent_memory()

    context = ""

    for m in memory:
        context += f"User: {m['user']}\nAssistant: {m['assistant']}\n"

    full_prompt = f"""
You are Irish, a personal AI assistant.

Conversation history:
{context}

User: {prompt}
Assistant:
"""

    response = ""

    for token in ask_ai(full_prompt):
        response += token
        yield token

    # store memory
    add_memory(
        prompt,
        response,
        mode=get_mode(),
        intent=classify_intent(prompt),
        source="ai_agent",
    )
