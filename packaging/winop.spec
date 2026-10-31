# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
base_dir = Path.cwd()

datas = [
    (str(base_dir / "scripts" / "Get-WinOpDiagnostics.ps1"), "scripts"),
]

a = Analysis(
    [str(base_dir / "app" / "main.py")],
    pathex=[str(base_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'psutil',
        'sqlite3',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'torch'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WinOptimizeAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windows GUI application (no popup console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WinOptimizeAI',
)
