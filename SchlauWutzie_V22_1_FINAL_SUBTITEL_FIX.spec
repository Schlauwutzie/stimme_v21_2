# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project = Path(SPECPATH).resolve()
asset_image = project / "assets" / "schlawutzie.png"
asset_intro = project / "assets" / "SchlauWutzie_KI_AI_Datacenter_Intro_V4_FINAL.mp4"
runtime = project / "whisper_runtime"
model = project / "whisper_models" / "ggml-small-q5_1.bin"

for item in [asset_image, asset_intro, runtime / "whisper-cli.exe", model]:
    if not item.exists():
        raise SystemExit(f"FEHLER: Build-Asset fehlt: {item}")

ff_datas, ff_binaries, ff_hidden = collect_all("imageio_ffmpeg")

winrt_modules = [
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.media.speechsynthesis",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
]
winrt_datas, winrt_binaries, winrt_hidden = [], [], []
for module in winrt_modules:
    datas, binaries, hidden = collect_all(module)
    winrt_datas.extend(datas)
    winrt_binaries.extend(binaries)
    winrt_hidden.extend(hidden)

winrt_hidden.extend([
    "winrt",
    "winrt.runtime",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.media.speechsynthesis",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
])

analysis = Analysis(
    [str(project / "app.py")],
    pathex=[str(project)],
    binaries=ff_binaries + winrt_binaries,
    datas=(
        ff_datas + winrt_datas + [
            (str(asset_image), "assets"),
            (str(asset_intro), "assets"),
            (str(runtime), "whisper_runtime"),
            (str(model), "whisper_models"),
        ]
    ),
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
    name="SchlauWutzie_V22_1_FINAL_SUBTITEL_FIX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
