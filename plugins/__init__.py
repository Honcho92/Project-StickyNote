"""
Pin-target plugin system.

A plugin is any module in this package that exposes:
    - NAME: str                       # short id, e.g. "window_title"
    - LABEL: str                      # human label, e.g. "App / Window title"
    - def matches(pattern, context) -> bool
          pattern: str stored on the note (e.g. "Notepad")
          context: dict with keys:
              "window_title": str
              "process_name": str
              "exe_path": str
    - def suggest(context) -> str     # suggested pattern for the current context

Add a new file here and register it in PLUGINS below to create new pin types
(e.g. pin-by-process-name, pin-by-file-path, pin-by-time-of-day).
"""

from . import window_title
from . import process_name

PLUGINS = {
    window_title.NAME: window_title,
    process_name.NAME: process_name,
}


def get(name):
    return PLUGINS.get(name, window_title)


def all_plugins():
    return list(PLUGINS.values())
