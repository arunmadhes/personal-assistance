PLAN_KEYWORDS = {
    "and",
    "then",
    "after",
    "save",
    "store",
    "analyze",
    "summarize",
    "report",
}

DEVICE_KEYWORDS = {
    "take photo",
    "take pic",
    "capture image",
    "record video",
    "start recording",
}

YES_WORDS = {"yes", "yeah", "yep", "save", "ok", "okay", "sure", "do it"}
NO_WORDS = {"no", "nope", "cancel", "skip", "not now", "don't save", "do not save"}

INTENT_FRIENDLY_LABELS = {
    "vision": "look through the camera",
    "market": "help with stock or trading analysis",
    "device": "manage your camera or device files",
    "system": "control a Windows app or setting",
    "file": "open or read saved outputs",
    "search": "search for information",
    "memory": "check our earlier conversation",
    "general": "just answer normally",
}

INTENT_REPLY_HINTS = {
    "vision": ("camera", "see", "look", "look through the camera", "analyze the scene"),
    "market": ("stock", "trade", "trading", "market", "watchlist", "journal", "nifty", "sensex"),
    "device": ("device", "photo", "photos", "video", "videos", "camera files", "saved photos"),
    "system": ("system", "windows", "app", "setting", "open app", "control setting"),
    "file": ("file", "files", "saved output", "outputs", "read file", "open output"),
    "search": ("search", "internet", "look it up", "find info", "find information"),
    "memory": ("memory", "remember", "conversation", "history", "earlier chat"),
    "general": ("general", "normal", "answer", "just answer", "regular reply"),
}

COMMAND_CLARIFICATIONS = [
    {
        "triggers": ("take snap", "snap"),
        "options": [
            {
                "key": "photo",
                "label": "take a camera photo",
                "command": "take photo",
            },
            {
                "key": "screenshot",
                "label": "take a screenshot of the current screen",
                "command": "take screenshot",
            },
        ],
    },
    {
        "triggers": ("display pic", "display photo", "display image", "show pic", "show image"),
        "options": [
            {
                "key": "saved_photo",
                "label": "show your saved photos",
                "command": "show photos",
            },
            {
                "key": "camera_view",
                "label": "look through the camera right now",
                "command": "what do you see",
            },
        ],
    },
]

COMMAND_STYLE_PREFIXES = (
    "take",
    "show",
    "display",
    "open",
    "list",
    "read",
    "record",
    "launch",
    "capture",
)

COMMON_TYPO_MAP = {
    "teke": "take",
    "taek": "take",
    "phto": "photo",
    "phote": "photo",
    "picc": "pic",
    "disply": "display",
    "rekord": "record",
    "vedio": "video",
    "vido": "video",
    "opan": "open",
    "setings": "settings",
    "screnshot": "screenshot",
    "screenhot": "screenshot",
}

NATURAL_LANGUAGE_ALIASES = [
    (r"\b(price|quote|ltp|cmp)\s+(of\s+)?([A-Za-z][A-Za-z0-9&.-]{1,14})\b", r"quote \3"),
    (r"\b(analyze|analyse|review|check)\s+(the\s+)?(stock|share|chart)\s+([A-Za-z][A-Za-z0-9&.-]{1,14})\b", r"analyze \4 stock"),
    (r"\b(intraday)\s+(analysis|setup|trade)\s+(for\s+)?([A-Za-z][A-Za-z0-9&.-]{1,14})\b", r"intraday analyze \4 stock"),
    (r"\b(swing)\s+(analysis|setup|trade)\s+(for\s+)?([A-Za-z][A-Za-z0-9&.-]{1,14})\b", r"swing analyze \4 stock"),
    (r"\b(long\s*term|longterm|positional)\s+(analysis|setup|trade|view)\s+(for\s+)?([A-Za-z][A-Za-z0-9&.-]{1,14})\b", r"positional analyze \4 stock"),
    (r"\b(add)\s+([A-Za-z][A-Za-z0-9&.-]{1,14})\s+(to\s+)?(my\s+)?watchlist\b", r"add \2 to watchlist"),
    (r"\b(remove|delete)\s+([A-Za-z][A-Za-z0-9&.-]{1,14})\s+(from\s+)?(my\s+)?watchlist\b", r"remove \2 from watchlist"),
    (r"\b(show|review|check)\s+(my\s+)?watchlist\b", "show watchlist"),
    (r"\b(show|review)\s+(my\s+)?trade journal\b", "show trade journal"),
    (r"\b(how much should i risk on|risk for)\s+", "risk for "),
    (r"\b(take|click|capture)\s+(a\s+)?(pic|picture|photo)\b", "take photo"),
    (r"\b(take|grab|capture)\s+(a\s+)?(screen shot|screenshot|snapshot)\b", "take screenshot"),
    (r"\b(record|make)\s+(a\s+)?(clip|video)\b", "record video"),
    (r"\b(show|display)\s+(me\s+)?(my\s+)?(photos|photo|pics|pictures)\b", "show photos"),
    (r"\b(show|display)\s+(me\s+)?(my\s+)?(videos|video|clips)\b", "show videos"),
    (r"\b(open)\s+(me\s+)?(the\s+)?(photos|photo folder)\b", "open photos"),
    (r"\b(open)\s+(me\s+)?(the\s+)?(videos|video folder)\b", "open videos"),
    (r"\b(show|list)\s+(me\s+)?(my\s+)?(saved files|saved outputs|outputs)\b", "list outputs"),
    (r"\b(open)\s+(me\s+)?(the\s+)?(outputs|saved files|output folder)\b", "open outputs"),
    (r"\b(read|show|open)\s+(me\s+)?(the\s+)?latest\s+(saved\s+)?(file|output)\b", "read latest output"),
    (r"\b(look up|search for|find)\s+", "search "),
    (r"\b(what can you see|what do you see right now|look through the camera)\b", "what do you see"),
    (r"\b(open|launch|start)\s+(the\s+)?calculator\b", "open calculator"),
    (r"\b(open|launch|start)\s+(the\s+)?notepad\b", "open notepad"),
    (r"\b(open|launch|start)\s+(the\s+)?chrome\b", "open chrome"),
    (r"\b(open|launch|start)\s+(the\s+)?(file explorer|explorer)\b", "open explorer"),
    (r"\b(open|launch|start)\s+(the\s+)?settings\b", "open settings"),
    (r"\b(open|launch|start)\s+(the\s+)?task manager\b", "open task manager"),
    (r"\b(open|launch|start)\s+(the\s+)?power ?shell\b", "open powershell"),
    (r"\b(open|launch|start)\s+(the\s+)?command prompt\b", "open command prompt"),
]

COMMAND_REPLY_HINTS = {
    "photo": ("photo", "pic", "picture", "camera"),
    "screenshot": ("screenshot", "screen", "snapshot"),
    "saved_photo": ("saved photo", "saved photos", "photo", "photos", "pic", "picture", "gallery"),
    "camera_view": ("camera", "look", "see", "live view", "what do you see"),
    "saved_files": ("saved file", "saved files", "output", "outputs", "read file"),
    "search": ("search", "internet", "look it up", "find info"),
    "normal": ("normal", "answer", "just answer"),
}
