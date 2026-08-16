# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SchlauWutzie K.I. Video Studio V21.7 FINAL."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project = Path(SPECPATH).resolve()

assets = [
    project / "assets" / "schlawutzie.png",
    project / "assets" / "SchlauWutzie_KI_AI_Datacenter_Intro_V4_FINAL.mp4",
]
for asset in assets:
    if not asset.exists():
        raise SystemExit(f"FEHLER: Asset fehlt: {asset}")

datas = []
binaries = []
hidden = []

for package in [
    "imageio_ffmpeg",
    "faster_whisper",
    "ctranslate2",
    "av",
    "tokenizers",
]:
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas.extend(package_datas)
        binaries.extend(package_binaries)
        hidden.extend(package_hidden)
    except Exception:
        pass

winrt_modules = [
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.media.speechsynthesis",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
]

for module in winrt_modules:
    module_datas, module_binaries, module_hidden = collect_all(module)
    datas.extend(module_datas)
    binaries.extend(module_binaries)
    hidden.extend(module_hidden)

hidden.extend([
    "winrt",
    "winrt.runtime",
    "winrt.windows",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.media.speechsynthesis",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
    "faster_whisper",
    "ctranslate2",
    "av",
])

analysis = Analysis(
    [str(project / "app.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas + [
        (str(assets[0]), "assets"),
        (str(assets[1]), "assets"),
    ],
    hiddenimports=hidden,
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
    name="SchlauWutzie_V21_7_DEUTSCHE_AUTO_UNTERTITEL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
