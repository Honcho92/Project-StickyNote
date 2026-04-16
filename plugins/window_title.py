"""Match by a substring of the active window's title."""

NAME = "window_title"
LABEL = "Window title contains"


def matches(pattern, context):
    if not pattern:
        return False
    title = (context.get("window_title") or "").lower()
    return pattern.lower() in title


def suggest(context):
    """Return a reasonable default pattern for the current foreground window."""
    title = context.get("window_title") or ""
    if not title:
        return ""
    # Browsers & many apps use "Page - App Name" -> prefer the app-name tail
    for sep in (" - ", " — ", " | "):
        if sep in title:
            tail = title.rsplit(sep, 1)[-1].strip()
            if 2 < len(tail) < 40:
                return tail
    return title.strip()[:60]
