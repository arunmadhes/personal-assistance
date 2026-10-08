from datetime import datetime


state = {
    "pending_action": None,
    "data": {},
    "updated_at": None,
}


def set_pending(action, data=None):
    state["pending_action"] = action
    state["data"] = data or {}
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")


def get_pending():
    return state["pending_action"], state["data"]


def get_state_snapshot():
    return dict(state)


def clear_pending():
    state["pending_action"] = None
    state["data"] = {}
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
