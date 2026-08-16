# SchlauWutzie K.I. – Video Studio V22.3 FINAL

V22.3 targets the two remaining problems seen in the supplied test video:

1. subtitles appearing too low;
2. word timing not following the spoken audio closely enough.

## Synchronization upgrade

V22.3 replaces the Small q5_1 timestamp path with:

- `ggml-large-v3-turbo-q5_0`
- whisper.cpp v1.9.1
- `--dtw large.v3.turbo`
- `--output-json-full`

whisper.cpp exposes experimental token-level timestamps with DTW,
including `t_dtw`; the Large-v3-Turbo alignment-head preset is explicitly
supported. citeturn778414search0turn778414search1turn778414search3

The tokenizer data are reassembled into words, and those real word
spans drive the yellow karaoke timing.

## Visual change

Subtitles are moved substantially higher, to a safe zone above the
K.I. waveform.

Style:
- white unspoken text
- yellow spoken-word highlight
- black translucent caption background
- 1080x1920
- centered in the safe zone

## Performance

The q5_0 Large-v3-Turbo model is about 547 MiB. citeturn232201search1

V22.3 intentionally uses CPU mode for consistent behavior on Windows.
No CTranslate2 or System.Speech is used.

The original V21.5 StefanM/K.I.-bar pipeline and AI-Datacenter intro remain.

## Countdown-Intro Update

The V22.3 subtitle/transcription engine is intentionally unchanged.
Only the 8-second AI-Datacenter intro asset was replaced by
`assets/SchlauWutzie_AI_Datacenter_Intro_COUNTDOWN_FINAL.mp4`.

The GitHub build now explicitly verifies that the subtitle engine and
subtitle burn-in call are present before building the EXE.
