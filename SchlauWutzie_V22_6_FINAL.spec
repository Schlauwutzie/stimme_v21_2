# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
project = Path(SPECPATH).resolve()
asset_image = project / "assets" / "schlawutzie.png"
asset_intro = project / "assets" / "SchlauWutzie_NEW_INTRO_COUNTDOWN_FINAL.mp4"
for item in [asset_image, asset_intro]:
    if not item.exists():
        raise SystemExit(f"V22.6 Build-Asset fehlt: {item}")
packages = ["imageio_ffmpeg", "faster_whisper", "ctranslate2", "av", "onnxruntime", "huggingface_hub", "tokenizers", "requests"]
datas, binaries, hidden = [], [], []
for package in packages:
    d, b, h = collect_all(package)
    datas.extend(d); binaries.extend(b); hidden.extend(h)
datas.extend([(str(asset_image), "assets"), (str(asset_intro), "assets")])
hidden.extend(packages)
analysis = Analysis([str(project / "app.py")], pathex=[str(project)], binaries=binaries, datas=datas, hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, analysis.binaries, analysis.datas, [], name="SchlauWutzie_V22_6_FINAL", debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, disable_windowed_traceback=False, argv_emulation=False)
