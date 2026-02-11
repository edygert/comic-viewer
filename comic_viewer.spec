# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Comic Viewer
Build with: pyinstaller comic_viewer.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Collect all source modules
src_path = Path('src')
src_modules = [
    (str(f), 'src') for f in src_path.glob('*.py')
]

a = Analysis(
    ['comic_viewer.py'],
    pathex=[],
    binaries=[],
    datas=src_modules,  # Include src modules
    hiddenimports=[
        'PIL._tkinter_finder',  # Tkinter support for Pillow
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.Jpeg2KImagePlugin',  # JPEG 2000 support
        'natsort',
        'xxhash',
        'xdg_base_dirs',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Exclude unnecessary packages
        'numpy',
        'pandas',
    ],
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
    name='comic-viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression to reduce size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for error messages
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
