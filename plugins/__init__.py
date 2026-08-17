"""
Pin-target plugin system.

A plugin is any module in this package that exposes:
    - NAME: str                       # short id, e.g. "window_title"
    - LABEL: str                      # human label, e.g. "App / Window title"
    - PRO: bool (optional)            # True = requires a Pro license
    - def matches(pattern, context) -> bool
          pattern: str stored on the note (e.g. "Notepad")
          context: dict with keys:
              "window_title": str
              "process_name": str
              "exe_path": str
    - def suggest(context) -> str     # suggested pattern for the current context

Add a new file here and register it in PLUGINS below to create new pin types.
"""

from . import window_title
from . import process_name
from . import browser_url      # Pro
from . import file_path        # Pro
from . import time_of_day      # Pro

PLUGINS = {
    window_title.NAME: window_title,
    process_name.NAME: process_name,
    browser_url.NAME: browser_url,
    file_path.NAME: file_path,
    time_of_day.NAME: time_of_day,
}


def get(name):
    return PLUGINS.get(name, window_title)


def all_plugins():
    return list(PLUGINS.values())


def is_pro_plugin(name):
    return bool(getattr(get(name), "PRO", False))
