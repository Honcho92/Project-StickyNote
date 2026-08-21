# -*- mode: python ; coding: utf-8 -*-
# Build a single-file, windowed StickyNotes.exe:
#   python -m PyInstaller --noconfirm --clean StickyNotes.spec
from PyInstaller.utils.hooks import (
    collect_dynamic_libs, collect_data_files, collect_submodules,
)

block_cipher = None

# pystray/pywin32 pull their real backends in dynamically, and the pin plugins
# are imported as a package -- name them so PyInstaller bundles them.
_hidden = [
    'pystray._win32',
    'win32timezone',
    'licensing',
    'transcriber',
    'plugins',
    'plugins.window_title',
    'plugins.process_name',
    'plugins.browser_url',
    'plugins.file_path',
    'plugins.time_of_day',
    'numpy',
    'sounddevice',
    'pywhispercpp',
    'pywhispercpp.model',
]

# Voice-note native deps: whisper.cpp (pywhispercpp) + PortAudio (sounddevice).
# Collected defensively so the build still succeeds if they're not installed.
_binaries = []
_datas = []
for _pkg in ('pywhispercpp', 'sounddevice', '_sounddevice_data'):
    try:
        _binaries += collect_dynamic_libs(_pkg)
    except Exception:
        pass
    try:
        _datas += collect_data_files(_pkg)
    except Exception:
        pass
try:
    _hidden += collect_submodules('pywhispercpp')
except Exception:
    pass

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StickyNotes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # native ML/audio DLLs + UPX can corrupt; keep off
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # no console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    version='version_info.txt',
)
