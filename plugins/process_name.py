"""Match by the process executable name (e.g. 'notepad.exe', 'chrome.exe')."""

NAME = "process_name"
LABEL = "Process / .exe name"


def matches(pattern, context):
    if not pattern:
        return False
    proc = (context.get("process_name") or "").lower()
    p = pattern.lower().strip()
    # allow "notepad" or "notepad.exe"
    if not p.endswith(".exe"):
        p = p + ".exe"
    return proc == p


def suggest(context):
    return context.get("process_name") or ""
