from ai_router import ask_ai


def create_plan(goal):

    # 🔒 Normalize goal
    goal_clean = goal.strip().lower()

    # =========================
    # 🧠 STRICT PROMPT
    # =========================
    prompt = f"""
You are a task planning AI.

Your job is to break the given goal into clear, minimal, executable steps.

STRICT RULES:
- ONLY use the given goal
- DO NOT change topic
- DO NOT add unrelated examples
- DO NOT explain anything
- DO NOT include paragraphs
- ONLY return steps

TOPIC MUST REMAIN EXACTLY: "{goal_clean}"

FORMAT:
1. step
2. step
3. step

Goal: {goal_clean}

Steps:
"""

    # =========================
    # 🔁 GET RESPONSE
    # =========================
    response = ""

    for token in ask_ai(prompt):
        response += token

    # =========================
    # 🧹 CLEAN RESPONSE
    # =========================
    raw_lines = response.split("\n")

    steps = []

    for line in raw_lines:
        line = line.strip()

        # keep only numbered steps
        if not line:
            continue

        if not (line[0].isdigit() and "." in line[:3]):
            continue

        # remove numbering (1. , 2. etc)
        step_text = line.split(".", 1)[1].strip()

        if step_text:
            steps.append(step_text)

    # =========================
    # 🚫 FILTER IRRELEVANT STEPS
    # =========================
    goal_keywords = set(goal_clean.split())

    clean_steps = []

    for step in steps:
        step_words = set(step.lower().split())

        # keep step if it overlaps with goal keywords
        if step_words & goal_keywords:
            clean_steps.append(step)

    # fallback (if everything filtered out)
    if not clean_steps:
        clean_steps = steps

    # =========================
    # ✂️ LIMIT STEPS (CONTROL)
    # =========================
    return clean_steps[:5]