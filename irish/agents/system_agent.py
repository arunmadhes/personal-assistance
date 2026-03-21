import os
import subprocess


OPEN_COMMANDS = [
    (("open chrome", "launch chrome", "start chrome"), "Opening Chrome.", ["cmd", "/c", "start", "", "chrome"]),
    (("open notepad", "launch notepad", "start notepad"), "Opening Notepad.", ["notepad"]),
    (("open calculator", "launch calculator", "start calculator", "open calc"), "Opening Calculator.", ["calc"]),
    (("open explorer", "open file explorer", "launch explorer"), "Opening File Explorer.", ["explorer"]),
    (("open settings", "launch settings", "open windows settings"), "Opening Settings.", ["cmd", "/c", "start", "ms-settings:"]),
    (("open task manager", "launch task manager"), "Opening Task Manager.", ["taskmgr"]),
    (("open command prompt", "open cmd", "launch cmd"), "Opening Command Prompt.", ["cmd"]),
    (("open powershell", "launch powershell"), "Opening PowerShell.", ["powershell"]),
    (("open control panel", "launch control panel"), "Opening Control Panel.", ["control"]),
]


def _run_command(command):
    try:
        if len(command) == 1 and command[0] == "explorer":
            os.startfile("explorer")
        else:
            subprocess.Popen(command)
        return True, None
    except Exception as exc:
        return False, str(exc)


def handle(command):
    cmd = command.lower().strip()

    if "mute" in cmd or "unmute" in cmd or "volume" in cmd:
        yield (
            "Volume control is not implemented yet. "
            "I can currently open apps like Chrome, Notepad, Calculator, Explorer, Settings, Task Manager, CMD, PowerShell, and Control Panel."
        )
        return

    for triggers, message, run_command in OPEN_COMMANDS:
        if any(trigger in cmd for trigger in triggers):
            ok, error = _run_command(run_command)
            if ok:
                yield message
            else:
                yield f"I couldn't run that system command: {error}"
            return

    yield (
        "System command not recognized. "
        "Try commands like open chrome, open notepad, open calculator, open explorer, open settings, open task manager, open cmd, or open powershell."
    )
