# SchlauWutzie K.I. – Video Studio V22.4 CAPCUT STYLE FINAL

Eigene CapCut-ähnliche Untertitel-Engine.

Die Sprach­erkennung nutzt whisper.cpp, aber die Timing-Auswertung verwendet
nicht mehr DTW-Token-Rekonstruktion.

Stattdessen:
- `--max-len 1`
- `--split-on-word`
- Segment `from/to` direkt als Wortzeit
- proportionaler Fallback nur bei mehreren Wörtern in einem Segment
- gelbe Karaoke-Hervorhebung
- hohe Untertitelposition oberhalb der Waveform

whisper.cpp dokumentiert `--max-len` und `--split-on-word` als
Wort-Splitting-Modus. citeturn874204search0turn874204search1
