V21.8.3 FIX

The runtime error in V21.8.2 was caused by using:
RecognizedWordUnit.AudioPosition / AudioDuration.

Some System.Speech versions do not expose those properties directly.

V21.8.3 uses the documented compatible API:
RecognitionResult.GetAudioForWordRange(word, word)
and reads:
RecognizedAudio.AudioPosition
RecognizedAudio.Duration

This provides per-word audio timing without Whisper/CTranslate2.
