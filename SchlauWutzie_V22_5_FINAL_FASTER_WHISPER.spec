# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project = Path(SPECPATH).resolve()
asset_image = project / "assets" / "schlawutzie.png"
asset_intro = project / "assets" / "SchlauWutzie_KI_AI_Datacenter_Intro_V4_FINAL.mp4"
model_dir = project / "models" / "faster-whisper-large-v3-turbo"

for item in [
    asset_image,
    asset_intro,
    model_dir / "config.json",
    model_dir / "model.bin",
    model_dir / "tokenizer.json",
]:
    if not item.exists():
        raise SystemExit(f"V22.5 Build-Asset fehlt: {item}")

packages = [
    "imageio_ffmpeg",
    "faster_whisper",
    "ctranslate2",
    "av",
    "onnxruntime",
    "huggingface_hub",
    "tokenizers",
]

datas = []
binaries = []
hidden = []

for package in packages:
    try:
        d, b, h = collect_all(package)
        datas.extend(d)
        binaries.extend(b)
        hidden.extend(h)
    except Exception as exc:
        raise SystemExit(
            f"V22.5: collect_all fehlgeschlagen für {package}: {exc}"
        )

hidden.extend([
    "faster_whisper",
    "ctranslate2",
    "av",
    "onnxruntime",
])

datas.extend([
    (str(asset_image), "assets"),
    (str(asset_intro), "assets"),
    (str(model_dir), "models/faster-whisper-large-v3-turbo"),
])

analysis = Analysis(
    [str(project / "app.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
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
    name="SchlauWutzie_V22_5_FINAL_FASTER_WHISPER",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
