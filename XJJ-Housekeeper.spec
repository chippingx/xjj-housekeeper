# -*- mode: python ; coding: utf-8 -*-

import os
import shutil
import sys


def _resolve_binary(name, env_keys):
    for key in env_keys:
        env_path = os.environ.get(key)
        if env_path and os.path.exists(env_path):
            return env_path
    resolved = shutil.which(name)
    if resolved:
        return resolved
    if sys.platform == "darwin":
        candidates = [
            f"/opt/homebrew/bin/{name}",
            f"/usr/local/bin/{name}",
            f"/usr/bin/{name}",
        ]
    else:
        candidates = [
            f"/usr/local/bin/{name}",
            f"/usr/bin/{name}",
            f"/bin/{name}",
        ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


_include_ffmpeg = os.environ.get("XJJ_INCLUDE_FFMPEG", "0").strip().lower() in ("1", "true", "yes")
_binaries = []
if _include_ffmpeg:
    _ffprobe_path = _resolve_binary("ffprobe", ["FFPROBE_PATH", "XJJ_FFPROBE_PATH"])
    _ffmpeg_path = _resolve_binary("ffmpeg", ["FFMPEG_PATH", "XJJ_FFMPEG_PATH"])
    if _ffprobe_path:
        _binaries.append((_ffprobe_path, "."))
    else:
        print("⚠️ ffprobe not found; it will not be bundled.", file=sys.stderr)
    if _ffmpeg_path:
        _binaries.append((_ffmpeg_path, "."))
    else:
        print("⚠️ ffmpeg not found; it will not be bundled.", file=sys.stderr)


a = Analysis(
    ['ui/tkinter/app.py'],
    pathex=[],
    binaries=_binaries,
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
    name='倩影の居',
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
    name='倩影の居',
)
app = BUNDLE(
    coll,
    name='倩影の居.app',
    icon='assets/logos/icon.icns',
    bundle_identifier=None,
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleGetInfoString": "倩影の居 1.0.0 (2026.2.14)",
    },
)
