# StickyNotes

Pin notes to apps, webpages, and anything else with a window. When the target
app/page is focused the note pops up; when you switch away it tucks itself
away. Notes with no pins behave like classic always-on-top sticky notes.

## Install (one time)

1. Make sure Python 3.9+ is installed and on your PATH.
   <https://www.python.org/downloads/>
2. Double-click **`install.bat`**.

## Run

Double-click **`run.bat`** — no console window, no visible main window, just a
🟡 sticky-note icon in your system tray (click the ^ arrow near the clock).
If something misbehaves, use `run-debug.bat` instead to see errors.

*Auto-start on login:* press `Win+R`, type `shell:startup`, hit Enter, and drop
a shortcut to `run.bat` in that folder.

## Using it

| Action | How |
|---|---|
| New note | Tray icon → **New note**, or click **+** on any note |
| Move / resize | Drag the top bar / the bottom-right corner |
| Edit | Just type |
| Change color / opacity / font | Right-click anywhere on the note |
| Pin to current app/page | Right-click → **Pin to current window**, or click 📌 |
| Fine-grained pin rules | Right-click → **Pin rules…** |
| Hide a note (keep it) | Click **–** (bring it back via tray → *Show all hidden*) |
| Delete a note | Click **×** |
| Exit | Tray icon → **Exit** |

### How pinning works

Each note has a list of **rules**. If *any* rule matches the currently focused
window, the note is shown. Two built-in rule types:

- **Window title contains** — e.g. `Gmail`, `Notepad`, `Visual Studio Code`.
  Pins by substring, case-insensitive. Works for most apps *and* webpages
  (browsers put the page title + site name in the window title).
- **Process / .exe name** — e.g. `notepad.exe`, `chrome.exe`. Pins to a whole
  application regardless of which window/page is open.

Notes with **no rules** are "floating" — always on top, always visible.

## Data

Your notes live in `notes/notes.json` next to the app. Back it up freely.
Errors (if any) go to `error.log`.

## Extending it

The pinning system is plugin-based. Each file in `plugins/` exposes
`NAME`, `LABEL`, `matches(pattern, context)`, `suggest(context)`. Add a file,
register it in `plugins/__init__.py`, and it shows up in the Pin-rules dialog.

Ideas we haven't built yet:

- `browser_url.py` + a companion Chrome/Edge extension for true URL matching
  (today we match by window title, which for browsers is
  `"Page Title - Google Chrome"` — works well but can't disambiguate two
  Gmail tabs).
- `file_path.py` — "show when this file is open in any editor".
- `time_of_day.py` — "show only between 9am and 5pm".
- `workspace.py` — tag notes into workspaces and toggle a whole set.

Say the word and we'll add them.
