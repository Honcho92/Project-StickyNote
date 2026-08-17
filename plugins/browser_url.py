"""(Pro) Pin a note to a website.

Browsers put "Page Title - Site - Browser" in their window title, so matching a
domain or site keyword against the title pins a note to that site. Enter
something like ``gmail.com``, ``github``, or ``https://news.ycombinator.com``.

(Exact per-tab URL matching would need a companion browser extension; this
title-based match handles the common case well and needs nothing extra.)
"""

NAME = "browser_url"
LABEL = "Website / URL (Pro)"
PRO = True


def matches(pattern, context):
    if not pattern:
        return False
    title = (context.get("window_title") or "").lower()
    p = pattern.lower().strip()
    for cut in ("https://", "http://", "www."):
        if p.startswith(cut):
            p = p[len(cut):]
    p = p.split("/")[0].strip()          # keep the domain part
    if not p:
        return False
    label = p.split(".")[0] if "." in p else p   # "gmail" from "gmail.com"
    return p in title or (len(label) >= 3 and label in title)


def suggest(context):
    title = context.get("window_title") or ""
    for sep in (" - ", " — ", " | "):
        if sep in title:
            tail = title.rsplit(sep, 1)[-1].strip()
            if 2 < len(tail) < 40:
                return tail
    return title.strip()[:40]
