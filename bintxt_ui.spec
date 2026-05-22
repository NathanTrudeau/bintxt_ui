# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for bintxt_ui
# Build: pyinstaller bintxt_ui.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('logo.png', '.'),
        ('bintxt/core', 'bintxt/core'),   # include submodule core package
    ],
    hiddenimports=[
        'bintxt.core',
        'bintxt.core.ansi',
        'bintxt.core.yaml_loader',
        'bintxt.core.config',
        'bintxt.core.state',
        'bintxt.core.logger',
        'bintxt.core.operations',
        'bintxt.core.fs',
        'bintxt.core.pipeline',
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
    name='bintxt_ui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.png',   # Windows will use this as the .exe icon if it's a valid .ico
)
