# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ui/tkinter/app.py'],
    pathex=[],
    binaries=[],
    datas=[('i18n', 'i18n'), ('output', 'output'), ('tools/video_info_collector/config.yaml', 'tools/video_info_collector'), ('tools/filename_formatter/rename_rules.yaml', 'tools/filename_formatter')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='XJJ-Housekeeper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='XJJ-Housekeeper.app',
    icon=None,
    bundle_identifier=None,
)
