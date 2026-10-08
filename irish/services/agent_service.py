from brain import agent_brain
from agent import process_command


def build_agent_request(message, *, source="chat_ui", tab_id=None, metadata=None):
    return agent_brain({
        "message": message,
        "source": source,
        "tab_id": tab_id,
        "metadata": metadata or {},
    })


def stream_agent_response(message, *, source="chat_ui", tab_id=None, metadata=None):
    request = build_agent_request(
        message,
        source=source,
        tab_id=tab_id,
        metadata=metadata,
    )
    yield from process_command(request)
