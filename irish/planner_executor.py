from intent_classifier import classify_intent

from agents.ai_agent import handle as ai_agent
from agents.search_agent import handle as search_agent
from agents.system_agent import handle as system_agent
from agents.device_agent import handle as device_agent
from agents.file_agent import handle as file_agent
from agents.market_agent import handle as market_agent
from agent_manager import add_context_entry, create_sub_agent, summarize_shared_context


def _select_sub_agent(step, intent):
    step_lower = step.lower()

    if "save" in step_lower:
        return "archivist"
    if intent == "search":
        return "researcher"
    if intent == "market":
        return "market_analyst"
    if intent == "system":
        return "operator"
    if intent == "device":
        return "device_specialist"
    if any(word in step_lower for word in ("summarize", "write", "report", "explain")):
        return "writer"
    return "coordinator"


def execute_step(step, context, user_command, task_id=None):

    step_lower = step.lower().strip()

    # =========================
    # 🔥 PRIORITY: SAVE CHECK
    # =========================
    if "save" in step_lower:

        result = ""

        # fallback if context empty
        content_to_save = context.strip() if context.strip() else "No content generated."
        agent_name = "archivist"

        if task_id:
            create_sub_agent(task_id, agent_name, f"Save outputs for: {user_command}")
            add_context_entry(task_id, agent_name, f"Preparing to save content for step: {step}", kind="plan")

        for token in file_agent(content_to_save, user_command):
            result += token

        if task_id:
            add_context_entry(task_id, agent_name, result.strip(), kind="result")

        return result

    # =========================
    # 🎯 INTENT DETECTION
    # =========================
    intent = classify_intent(step)
    intent = intent.strip().lower().split()[0]
    agent_name = _select_sub_agent(step, intent)

    if task_id:
        create_sub_agent(task_id, agent_name, f"Execute step: {step}")

    result = ""

    # =========================
    # 🌐 SEARCH
    # =========================
    if intent == "search":
        if task_id:
            add_context_entry(task_id, agent_name, f"Researching: {step}", kind="plan")
        for token in search_agent(step):
            result += token

    # =========================
    # ⚙️ SYSTEM
    # =========================
    elif intent == "system":
        if task_id:
            add_context_entry(task_id, agent_name, f"System action: {step}", kind="plan")
        for token in system_agent(step):
            result += token

    elif intent == "market":
        if task_id:
            add_context_entry(task_id, agent_name, f"Market analysis: {step}", kind="plan")
        for token in market_agent(step):
            result += token

    # =========================
    # 💻 DEVICE
    # =========================
    elif intent == "device":
        if task_id:
            add_context_entry(task_id, agent_name, f"Device action: {step}", kind="plan")
        for token in device_agent(step):
            result += token

    # =========================
    # 🧠 AI (STRICT CONTEXT USE)
    # =========================
    else:
        shared_context = context
        if task_id:
            task_context = summarize_shared_context(task_id)
            shared_context = "\n".join(part for part in [context, task_context] if part).strip()
            add_context_entry(task_id, agent_name, f"Reasoning about step: {step}", kind="plan")

        prompt = f"""
You are executing ONE step of a plan.

STRICT RULES:
- Follow ONLY the given step
- Use context ONLY if relevant
- DO NOT repeat previous outputs
- DO NOT add extra explanation
- Keep output short and direct

User Goal: {user_command}

Context:
{shared_context}

Current Step:
{step}

Output:
"""

        for token in ai_agent(prompt):
            result += token

    result = result.strip()

    if task_id and result:
        add_context_entry(task_id, agent_name, result, kind="result")

    return result
