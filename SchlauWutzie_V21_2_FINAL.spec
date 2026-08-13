# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SchlauWutzie K.I. Video Studio V21.2."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project = Path(SPECPATH).resolve()
asset = project / "assets" / "schlawutzie.png"
if not asset.exists():
    raise SystemExit(f"FEHLER: Standardbild fehlt: {asset}")

ff_datas, ff_binaries, ff_hidden = collect_all("imageio_ffmpeg")

winrt_modules = [
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.media.speechsynthesis",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
]

winrt_datas = []
winrt_binaries = []
winrt_hidden = [
    "winrt",
    "winrt.runtime",
    "winrt.windows",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.media",
    "winrt.windows.media.speechsynthesis",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
]

for module in winrt_modules:
    datas, binaries, hidden = collect_all(module)
    winrt_datas.extend(datas)
    winrt_binaries.extend(binaries)
    winrt_hidden.extend(hidden)

analysis = Analysis(
    [str(project / "app.py")],
    pathex=[str(project)],
    binaries=ff_binaries + winrt_binaries,
    datas=ff_datas + winrt_datas + [(str(asset), "assets")],
    hiddenimports=ff_hidden + winrt_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="SchlauWutzie_V21_2_FINAL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
