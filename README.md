# V22.5 External Model FINAL

The 1.62 GB Faster-Whisper model is NOT bundled inside the EXE.

Folder layout:

SchlauWutzie_V22_5_EXTERNAL_MODEL_FINAL.exe
models/
  faster-whisper-large-v3-turbo/
    config.json
    model.bin
    preprocessor_config.json
    tokenizer.json
    vocabulary.json

The model is loaded with `local_files_only=True` from the folder next
to the EXE. This avoids the huge PyInstaller one-file extraction and
makes the actual model-loading failure visible.

The Faster-Whisper large-v3-turbo model repository is about 1.62 GB.
Its files include model.bin, config.json, preprocessor_config.json,
tokenizer.json and vocabulary.json. citeturn373741search0turn373741search1
