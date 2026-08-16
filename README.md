# SchlauWutzie K.I. – Video Studio V22.1 FINAL

V22.1 is a bug-fix release of V22.

## Important fix

The previous V22 could correctly create a subtitle `.ass` file but then
skip the burn-in step when `self.subtitle_path` already existed.

V22.1 always burns the generated/stored subtitle file into the spoken
main video before the clean AI-Datacenter intro is prepended.

Pipeline:

**StefanM → K.I.-Animation → whisper.cpp word timestamps → subtitle burn-in → AI-Datacenter intro**

The intro itself remains clean; subtitles belong to the main spoken video.

The proven V21.5 core remains the base.
