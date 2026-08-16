# SchlauWutzie K.I. – Video Studio V22 FINAL

V22 ist die neue endgültige Auto-Untertitel-Engine.

## Auto-Untertitel

Die V22 verwendet **whisper.cpp v1.9.1** mit dem mehrsprachigen
**Whisper Small q5_1** Modell.

Das Modell ist für Deutsch geeignet und wird während des GitHub-Builds
in die EXE eingebaut. Beim normalen Start ist kein Modell-Download nötig.

Die Erkennung verwendet:

- Deutsch fest als Sprache
- Wort-Level-Timestamps mit `--max-len 1`
- nur einen Whisper-Prozessor, um Timestamp-Grenzfehler zu vermeiden
- 5er Beam Search
- den eingefügten Originaltext als Initial Prompt für bessere Erkennung
  von Namen, Zahlen und Eigennamen

## V22 Funktionen

- Microsoft Stefan / OneCore
- Copy & Paste
- AI-Datacenter-Intro
- reaktive K.I.-Balken
- deutsche Auto-Untertitel
- Karaoke-artige Wort-Hervorhebung
- 9:16 / 1080×1920
- MP4-Export

## Ziel

Der Ablauf:

**Text einfügen → StefanM → Deutsche Auto-Untertitel → Vorschau → MP4**

Die Auto-Untertitel werden direkt in die fertige MP4 eingebrannt.

## Technischer Hinweis

whisper.cpp ist eine C/C++-Implementierung von Whisper ohne den
CTranslate2/Python-ML-Stack der V21.7/V21.8. Die offizielle v1.9.1
Release unterstützt Windows und CPU-only inference.

Das Whisper-Small-q5_1-Modell ist etwa 190 MB groß.
