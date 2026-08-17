# SchlauWutzie K.I. – Video Studio V22.5 FINAL

## Neue Untertitel-Engine

V22.5 replaces the unstable whisper.cpp DTW-token reconstruction with
**faster-whisper large-v3-turbo**.

The current faster-whisper API provides native word-level timestamps,
Silero VAD, and explicitly documents `condition_on_previous_text=False`
as a way to reduce long-form repetition loops / timestamp drift.
It also supports `hallucination_silence_threshold`. citeturn464751search0turn464751search1

The `large-v3-turbo` model is a supported faster-whisper model and its
conversion is mapped to `mobiuslabsgmbh/faster-whisper-large-v3-turbo`.
citeturn806556search1

## V22.5 anti-repetition strategy

- `condition_on_previous_text=False`
- native `word_timestamps=True`
- Silero VAD
- `hallucination_silence_threshold=1.0`
- `repetition_penalty=1.08`
- `no_repeat_ngram_size=3`
- temperature fallback
- automatic second pass if an obvious repetition loop is detected

This directly targets the failure pattern seen in the test video,
where a single word repeated for many seconds. Current whisper.cpp
issues/discussions document this class of long-form repetition
hallucinations and the role of previous-text conditioning/fallback.
citeturn652282search3turn652282search5

The StefanM voice, K.I. animation, original intro and MP4 export are
kept from the Perfekt basis. This package does not change the intro.
