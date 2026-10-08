from ai_router import ask_ai, get_mode
from memory import add_memory, get_recent_memory


def handle(prompt, request_context=None):
    request_context = request_context or {}
    memory = request_context.get("memory")
    if memory is None:
        memory = get_recent_memory()

    context = ""
    for item in memory:
        context += f"User: {item['user']}\nAssistant: {item['assistant']}\n"

    full_prompt = f"""
You are Irish, acting as an Arduino code generation specialist.

Current mode: {request_context.get("mode", get_mode())}

Conversation history:
{context}

User request:
{prompt}

Instructions:
- Focus on Arduino sketches, wiring assumptions, sensors, actuators, and serial debugging.
- Prefer complete, runnable Arduino C++ code when the user asks for code.
- Include required libraries only when needed.
- Use clear pin names, constants, setup(), and loop().
- If the request is underspecified, make reasonable assumptions and state them briefly.
- Keep the response practical and implementation-focused.
- If code is the main output, provide the sketch first.

Assistant:
"""

    response = ""

    for token in ask_ai(full_prompt):
        response += token
        yield token

    add_memory(
        prompt,
        response,
        mode=request_context.get("mode", get_mode()),
        intent="arduino",
        source="arduino_agent",
    )
