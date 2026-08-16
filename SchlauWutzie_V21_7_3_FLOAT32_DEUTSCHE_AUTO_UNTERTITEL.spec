# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project = Path(SPECPATH).resolve()
asset_image = project / "assets" / "schlawutzie.png"
asset_intro = project / "assets" / "SchlauWutzie_KI_AI_Datacenter_Intro_V4_FINAL.mp4"
asset_model = project / "assets" / "whisper-base"

required = [
    asset_image,
    asset_intro,
    asset_model / "config.json",
    asset_model / "model.bin",
    asset_model / "tokenizer.json",
    asset_model / "vocabulary.txt",
]
for item in required:
    if not item.exists():
        raise SystemExit(f"FEHLER: Build-Asset fehlt: {item}")

ff_datas, ff_binaries, ff_hidden = collect_all("imageio_ffmpeg")
fw_datas, fw_binaries, fw_hidden = collect_all("faster_whisper")
ct_datas, ct_binaries, ct_hidden = collect_all("ctranslate2")

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
    binaries=ff_binaries + fw_binaries + ct_binaries + winrt_binaries,
    datas=(
        ff_datas + fw_datas + ct_datas + winrt_datas
        + [
            (str(asset_image), "assets"),
            (str(asset_intro), "assets"),
            (str(asset_model), "assets/whisper-base"),
        ]
    ),
    hiddenimports=ff_hidden + fw_hidden + ct_hidden + winrt_hidden,
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
    name="SchlauWutzie_V21_7_3_FLOAT32_DEUTSCHE_AUTO_UNTERTITEL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
