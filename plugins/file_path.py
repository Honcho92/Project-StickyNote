"""(Pro) Show a note when a particular file is open.

Editors put the file name in the window title (e.g. ``report.docx - Word``), so
entering a file name pins the note to that file in any editor. You can enter
just ``report.docx`` or a full path (only the file name is matched).
"""

import os
import re

NAME = "file_path"
LABEL = "File is open (Pro)"
PRO = True


def matches(pattern, context):
    if not pattern:
        return False
    title = (context.get("window_title") or "").lower()
    name = os.path.basename(pattern.strip().replace("\\", "/")).lower()
    return bool(name) and name in title


def suggest(context):
    title = context.get("window_title") or ""
    m = re.search(r"[\w\-. ]+\.\w{1,5}", title)   # first filename-looking token
    return m.group(0).strip() if m else ""
