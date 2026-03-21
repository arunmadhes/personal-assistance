import uuid
from datetime import datetime


active_tasks = {}
task_history = []


def create_task(agent_type, message):
    task_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat(timespec="seconds")

    active_tasks[task_id] = {
        "id": task_id,
        "agent": agent_type,
        "message": message,
        "status": "created",
        "created_at": created_at,
        "updated_at": created_at,
        "result": "",
        "shared_context": [],
        "sub_agents": {},
    }

    return task_id


def update_task(task_id, status, result=None):
    task = active_tasks.get(task_id)
    if not task:
        return

    task["status"] = status
    task["updated_at"] = datetime.now().isoformat(timespec="seconds")

    if result is not None:
        task["result"] = result

    if status in {"completed", "failed"}:
        task_history.append(dict(task))


def get_task(task_id):
    return active_tasks.get(task_id)


def get_active_tasks():
    return list(active_tasks.values())


def get_task_history(limit=20):
    return task_history[-limit:]


def get_latest_task():
    if active_tasks:
        return max(active_tasks.values(), key=lambda task: task["updated_at"])
    if task_history:
        return task_history[-1]
    return None


def create_sub_agent(task_id, role, objective):
    task = active_tasks.get(task_id)
    if not task:
        return None

    role_key = role.strip().lower()
    sub_agents = task["sub_agents"]

    if role_key in sub_agents:
        return sub_agents[role_key]

    agent_id = f"{role_key}-{str(uuid.uuid4())[:6]}"
    profile = {
        "id": agent_id,
        "role": role_key,
        "objective": objective,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "last_output": "",
    }
    sub_agents[role_key] = profile
    task["updated_at"] = datetime.now().isoformat(timespec="seconds")
    return profile


def add_context_entry(task_id, agent_name, content, kind="note"):
    task = active_tasks.get(task_id)
    if not task:
        return

    entry = {
        "agent": agent_name,
        "kind": kind,
        "content": content.strip(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    task["shared_context"].append(entry)
    task["updated_at"] = entry["timestamp"]

    sub_agent = task["sub_agents"].get(agent_name)
    if sub_agent is not None:
        sub_agent["last_output"] = content.strip()


def get_shared_context(task_id):
    task = active_tasks.get(task_id)
    if not task:
        return []
    return list(task["shared_context"])


def summarize_shared_context(task_id, limit=6):
    entries = get_shared_context(task_id)[-limit:]
    lines = []

    for entry in entries:
        content = entry["content"]
        if not content:
            continue
        lines.append(f"{entry['agent']} ({entry['kind']}): {content}")

    return "\n".join(lines)
