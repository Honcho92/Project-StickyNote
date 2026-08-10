"""
StickyNotes - pin notes to apps, webpages, or anything with a window title.

Architecture
------------
- Notes are plain dicts serialized to notes/notes.json.
- Each note has a list of "pin rules": (plugin_name, pattern).
- A background thread polls the foreground window 2x/sec and reports a "context"
  (window_title, process_name, exe_path). Each note's rules are evaluated against
  that context; if any rule matches, the note shows (unless hidden by the user).
- If a note has no pin rules, it's treated as always-on-top floating.
- Plugins (plugins/*.py) decide how to match patterns against context, so we can
  add new pin types without touching this file.
"""

import json
import os
import shutil
import socket
import sys
import time
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

# Optional Windows integration
try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False

# System tray (optional; app still works without it)
# Note: importing pystray can raise more than ImportError (e.g. a ValueError when
# no suitable GUI backend/namespace is available), so catch broadly and just fall
# back to no-tray mode instead of crashing the whole app at import time.
try:
    import pystray
    from PIL import Image, ImageDraw
    HAVE_TRAY = True
except Exception:
    HAVE_TRAY = False

import plugins

# ---------------------------------------------------------------------------
APP_NAME = "StickyNotes"
APP_VERSION = "1.0.0"


def _data_dir():
    """Per-user, always-writable data directory.

    Notes must not live next to the program: once StickyNotes is installed to a
    read-only location (e.g. Program Files) or run as a packaged one-file .exe,
    the app folder isn't writable. %APPDATA%\\StickyNotes always is.
    """
    base = (os.environ.get("APPDATA")            # Windows
            or os.environ.get("XDG_DATA_HOME")   # Linux
            or os.path.expanduser("~"))
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


APP_DIR = Path(__file__).parent
DATA_DIR = _data_dir()
NOTES_FILE = DATA_DIR / "notes.json"
ERROR_LOG = DATA_DIR / "error.log"

# One-time migration: older builds stored notes next to the app.
_OLD_NOTES = APP_DIR / "notes" / "notes.json"
if _OLD_NOTES.exists() and not NOTES_FILE.exists():
    try:
        shutil.copyfile(_OLD_NOTES, NOTES_FILE)
    except Exception:
        pass

# Keep a single instance: two copies writing notes.json would clobber each other.
_INSTANCE_LOCK = None


def _acquire_single_instance():
    """True if we're the only running instance.

    Binds a fixed localhost port as a lock; the OS releases it automatically if
    the process exits or crashes, so there's no stale lock file to clean up.
    """
    global _INSTANCE_LOCK
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 49713))
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        return False
    s.listen(1)
    _INSTANCE_LOCK = s  # hold the reference for the process lifetime
    return True

COLORS = {
    "Yellow": "#FFF4A3",
    "Green":  "#C8E6C9",
    "Blue":   "#BBDEFB",
    "Pink":   "#F8BBD0",
    "Orange": "#FFCC80",
    "Purple": "#E1BEE7",
    "Gray":   "#ECEFF1",
}
DEFAULT_COLOR = "Yellow"
POLL_INTERVAL = 0.4  # seconds


def darken(hex_color, factor=0.85):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


# ---------------------------------------------------------------------------
# Foreground-window detection
# ---------------------------------------------------------------------------
def get_foreground_context():
    """Return {window_title, process_name, exe_path, hwnd} for the active window."""
    ctx = {"window_title": "", "process_name": "", "exe_path": "", "hwnd": 0}
    if not win32gui:
        return ctx
    try:
        hwnd = win32gui.GetForegroundWindow()
        ctx["hwnd"] = hwnd
        ctx["window_title"] = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid and HAVE_PSUTIL:
            try:
                p = psutil.Process(pid)
                ctx["process_name"] = p.name()
                ctx["exe_path"] = p.exe()
            except Exception:
                pass
    except Exception:
        pass
    return ctx


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class NoteData:
    """Plain data for a note (serializable)."""

    def __init__(self, nid, **kw):
        self.id = nid
        self.content = kw.get("content", "")
        self.x = kw.get("x", 120)
        self.y = kw.get("y", 120)
        self.width = kw.get("width", 260)
        self.height = kw.get("height", 220)
        self.color = kw.get("color", DEFAULT_COLOR)
        self.opacity = kw.get("opacity", 1.0)     # 0.3 - 1.0
        self.font_size = kw.get("font_size", 11)
        self.hidden_by_user = kw.get("hidden_by_user", False)
        # pin_rules is a list of [plugin_name, pattern]
        self.pin_rules = kw.get("pin_rules", [])

    def to_dict(self):
        return {k: getattr(self, k) for k in (
            "id", "content", "x", "y", "width", "height", "color",
            "opacity", "font_size", "hidden_by_user", "pin_rules"
        )}

    def should_show(self, context):
        """Given a foreground context, should this note be visible?"""
        if self.hidden_by_user:
            return False
        if not self.pin_rules:
            return True  # floating, always on top
        for plugin_name, pattern in self.pin_rules:
            plugin = plugins.get(plugin_name)
            try:
                if plugin.matches(pattern, context):
                    return True
            except Exception:
                traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# Note window (UI)
# ---------------------------------------------------------------------------
class NoteWindow:
    def __init__(self, app, data):
        self.app = app
        self.data = data
        self.win = tk.Toplevel(app.root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{data.width}x{data.height}+{data.x}+{data.y}")
        self.win.attributes("-alpha", data.opacity)

        self._drag = {"x": 0, "y": 0}
        self._resize = {"x": 0, "y": 0, "w": 0, "h": 0}
        self._shown = False

        self._build_ui()
        self._apply_color()

    # ---- UI construction ---------------------------------------------------
    def _build_ui(self):
        c = COLORS.get(self.data.color, COLORS[DEFAULT_COLOR])
        d = darken(c)

        self.titlebar = tk.Frame(self.win, bg=d, height=26, cursor="fleur")
        self.titlebar.pack(fill="x", side="top")
        self.titlebar.pack_propagate(False)

        self.pin_label = tk.Label(
            self.titlebar, text=self._pin_label_text(),
            bg=d, fg="#333", font=("Segoe UI", 8), anchor="w",
        )
        self.pin_label.pack(side="left", padx=8)

        btns = tk.Frame(self.titlebar, bg=d)
        btns.pack(side="right", padx=2)

        def mkbtn(text, cmd, tip=""):
            b = tk.Button(
                btns, text=text, command=cmd, bg=d, fg="#222",
                relief="flat", bd=0, font=("Segoe UI", 10), cursor="hand2",
                activebackground=darken(d, 0.9), padx=4, pady=0,
            )
            b.pack(side="left")
            return b

        mkbtn("+", self.app.new_note)          # new sibling note
        mkbtn("🎨", self._cycle_color)
        mkbtn("📌", self.open_pin_dialog)
        mkbtn("–", self.hide_note)             # user-hide
        mkbtn("×", self.delete_note)           # delete

        # Text area
        self.text = tk.Text(
            self.win, wrap="word", relief="flat", bd=0,
            bg=c, fg="#111", insertbackground="#111",
            font=("Segoe UI", self.data.font_size),
            padx=10, pady=8,
        )
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", self.data.content)
        self.text.bind("<KeyRelease>", self._on_text_change)

        # Resize grip (bottom-right corner)
        self.grip = tk.Frame(self.win, bg=d, width=14, height=14, cursor="size_nw_se")
        self.grip.place(relx=1.0, rely=1.0, anchor="se")

        # Drag bindings on titlebar
        for w in (self.titlebar, self.pin_label):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_end)
            w.bind("<Button-3>", self._show_menu)

        # Resize bindings
        self.grip.bind("<Button-1>", self._resize_start)
        self.grip.bind("<B1-Motion>", self._resize_move)
        self.grip.bind("<ButtonRelease-1>", self._resize_end)

        self.text.bind("<Button-3>", self._show_menu)

        # Context menu
        self.menu = tk.Menu(self.win, tearoff=0)
        self.menu.add_command(label="Pin to current window", command=self.pin_to_current)
        self.menu.add_command(label="Pin rules…", command=self.open_pin_dialog)
        self.menu.add_separator()
        color_menu = tk.Menu(self.menu, tearoff=0)
        for name in COLORS:
            color_menu.add_command(label=name, command=lambda n=name: self._set_color(n))
        self.menu.add_cascade(label="Color", menu=color_menu)
        op_menu = tk.Menu(self.menu, tearoff=0)
        for pct in (100, 90, 75, 60, 45, 30):
            op_menu.add_command(label=f"{pct}%", command=lambda p=pct: self._set_opacity(p / 100))
        self.menu.add_cascade(label="Opacity", menu=op_menu)
        font_menu = tk.Menu(self.menu, tearoff=0)
        for sz in (9, 10, 11, 12, 14, 16, 20):
            font_menu.add_command(label=f"{sz} pt", command=lambda s=sz: self._set_font_size(s))
        self.menu.add_cascade(label="Font size", menu=font_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Hide (keep)", command=self.hide_note)
        self.menu.add_command(label="Delete note", command=self.delete_note)

    def _pin_label_text(self):
        if self.data.hidden_by_user:
            return "— hidden"
        n = len(self.data.pin_rules)
        if n == 0:
            return "floating"
        if n == 1:
            _, pat = self.data.pin_rules[0]
            return f"📌 {pat[:28]}"
        return f"📌 {n} rules"

    def _show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    # ---- Drag & resize -----------------------------------------------------
    def _drag_start(self, e):
        self._drag["x"] = e.x_root - self.win.winfo_x()
        self._drag["y"] = e.y_root - self.win.winfo_y()

    def _drag_move(self, e):
        self.win.geometry(f"+{e.x_root - self._drag['x']}+{e.y_root - self._drag['y']}")

    def _drag_end(self, _e):
        self.data.x = self.win.winfo_x()
        self.data.y = self.win.winfo_y()
        self.app.save()

    def _resize_start(self, e):
        self._resize.update(
            x=e.x_root, y=e.y_root,
            w=self.win.winfo_width(), h=self.win.winfo_height(),
        )

    def _resize_move(self, e):
        w = max(160, self._resize["w"] + (e.x_root - self._resize["x"]))
        h = max(100, self._resize["h"] + (e.y_root - self._resize["y"]))
        self.win.geometry(f"{w}x{h}")

    def _resize_end(self, _e):
        self.data.width = self.win.winfo_width()
        self.data.height = self.win.winfo_height()
        self.app.save()

    # ---- Actions -----------------------------------------------------------
    def _on_text_change(self, _e=None):
        self.data.content = self.text.get("1.0", "end-1c")
        self.app.save(debounced=True)

    def _cycle_color(self):
        names = list(COLORS.keys())
        i = names.index(self.data.color) if self.data.color in names else 0
        self._set_color(names[(i + 1) % len(names)])

    def _set_color(self, name):
        self.data.color = name
        self._apply_color()
        self.app.save()

    def _apply_color(self):
        c = COLORS.get(self.data.color, COLORS[DEFAULT_COLOR])
        d = darken(c)
        self.win.configure(bg=c)
        self.titlebar.configure(bg=d)
        self.pin_label.configure(bg=d)
        self.grip.configure(bg=d)
        self.text.configure(bg=c)
        for child in self.titlebar.winfo_children():
            try:
                child.configure(bg=d)
                for gc in child.winfo_children():
                    gc.configure(bg=d)
            except tk.TclError:
                pass

    def _set_opacity(self, v):
        self.data.opacity = v
        self.win.attributes("-alpha", v)
        self.app.save()

    def _set_font_size(self, sz):
        self.data.font_size = sz
        self.text.configure(font=("Segoe UI", sz))
        self.app.save()

    def pin_to_current(self):
        ctx = self.app.last_context or get_foreground_context()
        suggestion = plugins.window_title.suggest(ctx)
        if not suggestion:
            messagebox.showwarning("StickyNotes", "No active window detected.", parent=self.win)
            return
        rule = ["window_title", suggestion]
        if rule not in self.data.pin_rules:
            self.data.pin_rules.append(rule)
            self.refresh_pin_label()
            self.app.save()
            messagebox.showinfo("StickyNotes", f"Pinned to: {suggestion}", parent=self.win)

    def open_pin_dialog(self):
        PinDialog(self.app, self)

    def refresh_pin_label(self):
        self.pin_label.configure(text=self._pin_label_text())

    def hide_note(self):
        self.data.hidden_by_user = True
        self.win.withdraw()
        self._shown = False
        self.refresh_pin_label()
        self.app.save()

    def delete_note(self):
        if messagebox.askyesno("Delete note", "Delete this note permanently?", parent=self.win):
            self.app.delete_note(self.data.id)

    # ---- Visibility --------------------------------------------------------
    def apply_visibility(self, context):
        """Called by the monitor loop to show/hide based on pin rules."""
        show = self.data.should_show(context)
        if show and not self._shown:
            self.win.deiconify()
            self.win.lift()
            self._shown = True
        elif not show and self._shown:
            self.win.withdraw()
            self._shown = False

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Pin-rules dialog
# ---------------------------------------------------------------------------
class PinDialog:
    def __init__(self, app, note_window):
        self.app = app
        self.nw = note_window
        self.data = note_window.data

        self.dlg = tk.Toplevel(app.root)
        self.dlg.title("Pin rules")
        self.dlg.geometry("440x420")
        self.dlg.transient(note_window.win)
        self.dlg.grab_set()

        tk.Label(self.dlg, text="Show this note when…",
                 font=("Segoe UI", 11, "bold")).pack(pady=(14, 2))
        tk.Label(self.dlg,
                 text="Any matching rule triggers the note. No rules = floating/always-on-top.",
                 font=("Segoe UI", 9), fg="#555", wraplength=400).pack(pady=(0, 10))

        list_frame = tk.Frame(self.dlg)
        list_frame.pack(fill="both", expand=True, padx=14)

        self.tree = ttk.Treeview(
            list_frame, columns=("type", "pattern"), show="headings", height=7,
        )
        self.tree.heading("type", text="Match type")
        self.tree.heading("pattern", text="Pattern")
        self.tree.column("type", width=150, anchor="w")
        self.tree.column("pattern", width=250, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self._refresh_list()

        btn_row = tk.Frame(self.dlg)
        btn_row.pack(fill="x", padx=14, pady=8)
        tk.Button(btn_row, text="Remove", command=self._remove).pack(side="left")
        tk.Button(btn_row, text="Clear all", command=self._clear).pack(side="left", padx=6)

        # Add new rule
        add = tk.LabelFrame(self.dlg, text="Add rule", padx=10, pady=8)
        add.pack(fill="x", padx=14, pady=(4, 10))

        tk.Label(add, text="Match type:").grid(row=0, column=0, sticky="w")
        self.type_var = tk.StringVar(value=plugins.window_title.NAME)
        type_combo = ttk.Combobox(
            add, textvariable=self.type_var, state="readonly",
            values=[p.NAME for p in plugins.all_plugins()],
        )
        type_combo.grid(row=0, column=1, sticky="ew", padx=6, pady=2)

        tk.Label(add, text="Pattern:").grid(row=1, column=0, sticky="w")
        self.pat_var = tk.StringVar()
        tk.Entry(add, textvariable=self.pat_var).grid(row=1, column=1, sticky="ew", padx=6, pady=2)
        add.columnconfigure(1, weight=1)

        ctx = self.app.last_context or get_foreground_context()
        suggestions_row = tk.Frame(add)
        suggestions_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        tk.Label(suggestions_row, text="Use current:", fg="#555").pack(side="left")
        for plugin in plugins.all_plugins():
            s = plugin.suggest(ctx)
            if s:
                tk.Button(
                    suggestions_row, text=f"{plugin.LABEL} → {s[:28]}",
                    command=lambda pn=plugin.NAME, pat=s: self._add(pn, pat),
                ).pack(side="left", padx=4)

        tk.Button(add, text="Add rule",
                  command=lambda: self._add(self.type_var.get(), self.pat_var.get().strip())
                  ).grid(row=3, column=1, sticky="e", pady=(6, 0))

        tk.Button(self.dlg, text="Done", command=self.dlg.destroy).pack(pady=8)

    def _refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, (ptype, pat) in enumerate(self.data.pin_rules):
            label = plugins.get(ptype).LABEL if ptype in plugins.PLUGINS else ptype
            self.tree.insert("", "end", iid=str(idx), values=(label, pat))

    def _add(self, ptype, pat):
        if not pat:
            return
        rule = [ptype, pat]
        if rule not in self.data.pin_rules:
            self.data.pin_rules.append(rule)
            self._refresh_list()
            self.nw.refresh_pin_label()
            self.app.save()
        self.pat_var.set("")

    def _remove(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self.data.pin_rules[idx]
        self._refresh_list()
        self.nw.refresh_pin_label()
        self.app.save()

    def _clear(self):
        self.data.pin_rules.clear()
        self._refresh_list()
        self.nw.refresh_pin_label()
        self.app.save()


# ---------------------------------------------------------------------------
# App controller
# ---------------------------------------------------------------------------
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("StickyNotes")

        self.notes = {}  # id -> NoteData
        self.windows = {}  # id -> NoteWindow
        self._next_id = 1
        self._save_job = None
        self._running = True
        self.last_context = None

        self._load()
        for data in self.notes.values():
            self._spawn_window(data)

        # System tray is preferred; fall back to a small control window if it's
        # unavailable (pystray missing, or its backend fails to start).
        self._tray_active = False
        if HAVE_TRAY:
            try:
                self._setup_tray()
                self._tray_active = True
            except Exception:
                traceback.print_exc()
        if not self._tray_active:
            self._setup_fallback_window()

        # Background thread to watch foreground window
        threading.Thread(target=self._monitor_loop, daemon=True).start()

        # If there were no saved notes, create a welcome note
        if not self.notes:
            self.new_note(content=(
                "👋 Welcome to StickyNotes!\n\n"
                "• Drag the top bar to move.\n"
                "• Drag the bottom-right corner to resize.\n"
                "• Right-click for color, opacity, font, pin rules.\n"
                "• Click 📌 to pin this note to the app or webpage\n"
                "   you're currently looking at — it'll hide itself\n"
                "   when you switch away, and pop back when you return.\n\n"
                "Use the tray icon (arrow near the clock) — or the small\n"
                "StickyNotes bar — to create more notes or exit."
            ))

    # ---- Storage -----------------------------------------------------------
    def _load(self):
        if not NOTES_FILE.exists():
            return
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            for item in payload.get("notes", []):
                nid = item["id"]
                self.notes[nid] = NoteData(nid, **{k: v for k, v in item.items() if k != "id"})
                self._next_id = max(self._next_id, nid + 1)
        except Exception:
            traceback.print_exc()

    def save(self, debounced=False):
        if debounced:
            if self._save_job:
                self.root.after_cancel(self._save_job)
            self._save_job = self.root.after(600, self._do_save)
        else:
            self._do_save()

    def _do_save(self):
        self._save_job = None
        try:
            payload = {"notes": [n.to_dict() for n in self.notes.values()]}
            tmp = NOTES_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            tmp.replace(NOTES_FILE)
        except Exception:
            traceback.print_exc()

    # ---- Note lifecycle ----------------------------------------------------
    def new_note(self, content=""):
        nid = self._next_id
        self._next_id += 1
        offset = (nid * 24) % 200
        data = NoteData(nid, content=content, x=160 + offset, y=140 + offset)
        self.notes[nid] = data
        self._spawn_window(data)
        self.save()

    def _spawn_window(self, data):
        nw = NoteWindow(self, data)
        self.windows[data.id] = nw

    @staticmethod
    def _root_hwnd(hwnd):
        """Top-level (root) HWND for a given window handle, or the handle itself."""
        if not hwnd or win32gui is None:
            return hwnd
        try:
            # GA_ROOT = 2 -> the root window of the owner chain, which is what
            # GetForegroundWindow() reports for a focused note.
            return win32gui.GetAncestor(hwnd, 2)
        except Exception:
            return hwnd

    def _is_own_window(self, hwnd):
        """True if `hwnd` (the current foreground window) is one of our notes.

        tk's winfo_id() returns the *child* content HWND, while
        GetForegroundWindow() returns the *top-level* HWND, so compare at the
        root-ancestor level rather than expecting the raw ids to be equal.
        """
        if not hwnd or win32gui is None:
            return False
        fg_root = self._root_hwnd(hwnd)
        for nw in self.windows.values():
            try:
                cid = int(nw.win.winfo_id())
            except Exception:
                continue
            if hwnd == cid or fg_root == cid:
                return True
            if fg_root == self._root_hwnd(cid):
                return True
        return False

    def delete_note(self, nid):
        if nid in self.windows:
            self.windows[nid].destroy()
            del self.windows[nid]
        if nid in self.notes:
            del self.notes[nid]
        self.save()

    def show_all(self):
        for data in self.notes.values():
            data.hidden_by_user = False
        for nw in self.windows.values():
            nw.refresh_pin_label()
        # Re-apply visibility right away so un-hidden notes come back immediately
        # (whether they display still depends on their pin rules) instead of
        # waiting for the next monitor tick.
        self._apply_visibility(self.last_context or {})
        self.save()

    # ---- Monitor loop ------------------------------------------------------
    def _monitor_loop(self):
        while self._running:
            try:
                ctx = get_foreground_context()
                # If our own sticky-note is focused, keep the previous context
                # so we don't hide pinned notes while the user edits them.
                hwnd = ctx.get("hwnd") or 0
                if self._is_own_window(hwnd) and self.last_context:
                    ctx = self.last_context
                else:
                    self.last_context = ctx
                self.root.after(0, self._apply_visibility, ctx)
            except Exception:
                traceback.print_exc()
            time.sleep(POLL_INTERVAL)

    def _apply_visibility(self, ctx):
        for nw in self.windows.values():
            nw.apply_visibility(ctx)

    # ---- System tray -------------------------------------------------------
    def _setup_tray(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([6, 6, 58, 58], fill="#FFF176", outline="#C9A227", width=2)
        d.polygon([(42, 6), (58, 22), (58, 6)], fill="#FDD835")
        for y in (24, 34, 44):
            d.line([(14, y), (50, y)], fill="#5D4037", width=2)

        def on_new(_i, _it): self.root.after(0, self.new_note)
        def on_show_all(_i, _it): self.root.after(0, self.show_all)
        def on_quit(_i, _it): self.root.after(0, self.quit)

        menu = pystray.Menu(
            pystray.MenuItem("New note", on_new, default=True),
            pystray.MenuItem("Show all hidden notes", on_show_all),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_quit),
        )
        self.tray = pystray.Icon("StickyNotes", img, "StickyNotes", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _setup_fallback_window(self):
        """Tiny always-on-top control bar for when there's no system tray, so
        the user can always create notes and exit cleanly."""
        win = tk.Toplevel(self.root)
        win.title("StickyNotes")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.quit)
        bar = tk.Frame(win, padx=8, pady=6)
        bar.pack()
        tk.Label(bar, text="StickyNotes", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        tk.Button(bar, text="New note", command=self.new_note).pack(side="left", padx=2)
        tk.Button(bar, text="Show all", command=self.show_all).pack(side="left", padx=2)
        tk.Button(bar, text="Exit", command=self.quit).pack(side="left", padx=2)
        self._fallback_win = win

    # ---- Shutdown ----------------------------------------------------------
    def quit(self):
        self._running = False
        self.save()
        if self._tray_active:
            try:
                self.tray.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self._running = False


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not _acquire_single_instance():
        # Already running — notify (best effort) and exit quietly.
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showinfo(APP_NAME, "StickyNotes is already running.")
            r.destroy()
        except Exception:
            pass
        sys.exit(0)
    try:
        App().run()
    except Exception:
        # Surface any crash to a log file since we launch via pythonw (no console)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write("\n---\n")
            traceback.print_exc(file=f)
        raise
