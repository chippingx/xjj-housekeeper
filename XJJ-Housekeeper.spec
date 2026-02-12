# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ui/tkinter/app.py'],
    pathex=[],
    binaries=[],
    datas=[('i18n', 'i18n'), ('config/app_meta.json', 'config'), ('tools/video_info_collector/config.yaml', 'tools/video_info_collector'), ('tools/filename_formatter/rename_rules.yaml', 'tools/filename_formatter')],
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
    [],
    exclude_binaries=True,
    name='千姫の居所',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logos/icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='千姫の居所',
)
app = BUNDLE(
    coll,
    name='千姫の居所.app',
    icon='assets/logos/icon.icns',
    bundle_identifier=None,
)
