# -*- mode: python ; coding: utf-8 -*-
# Build a single-file, windowed StickyNotes.exe:
#   python -m PyInstaller --noconfirm --clean StickyNotes.spec

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # pystray/pywin32 pull their real backends in dynamically, and the pin
    # plugins are imported as a package -- name them so PyInstaller bundles them.
    hiddenimports=[
        'pystray._win32',
        'win32timezone',
        'plugins',
        'plugins.window_title',
        'plugins.process_name',
    ],
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
    upx=True,
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
