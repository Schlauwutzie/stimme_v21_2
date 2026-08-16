# SchlauWutzie K.I. – Video Studio V21.8 FINAL

## Überblick

**SchlauWutzie K.I. – Video Studio V21.8 FINAL** ist das 9:16-Video-Studio für dein TikTok-Format.

Die V21.8 verbindet dein bestehendes V21.5-Design mit dem AI-Datacenter-Intro und einer integrierten deutschen Auto-Untertitelung.

## Enthalten

- **Microsoft Stefan / OneCore** als Sprachstimme
- **Copy & Paste** für Texte aus Browser, Word, Notepad usw.
- **AI-Datacenter-Intro** vor dem Hauptvideo
- **K.I.-Balkenanimation**, die sichtbar auf die Stimme reagiert
- **Deutsche Auto-Untertitel** direkt im Programm
- **TikTok-Format 9:16**
- **1080 × 1920 Ausgabe**
- **MP4-Export**

## Deutsche Auto-Untertitel

Die V21.8 verwendet für die deutsche Spracherkennung die **Windows System.Speech-Erkennung**.

Dabei wird ein installierter deutscher **de-DE-Spracherkenner** verwendet.

Die Untertitel werden automatisch zeitlich zugeordnet und anschließend direkt in die MP4 eingebrannt.

### Voraussetzung

Windows muss einen deutschen **de-DE-Spracherkenner** installiert haben.

Der GitHub-Build prüft diese Voraussetzung vor dem Erzeugen der EXE.

## Bedienablauf

1. Text in das Textfeld einfügen.
2. **STEFANM ERZEUGEN** drücken.
3. **DEUTSCHE AUTO-UNTERTITEL** drücken.
4. Untertitel erzeugen lassen.
5. **VORSCHAU** oder **MP4 SPEICHERN** verwenden.

## Design

Das Hauptvideo verwendet weiterhin das bestätigte Schlauwutzie-K.I.-Layout mit:

- zentralem K.I.-Bereich
- linker und rechter reaktiver Stimmenanimation
- deinem Schlauwutzie-K.I.-Bild
- AI-Datacenter-Intro

## Assets

Im Repository bleiben insbesondere diese Dateien erhalten:

```text
assets/schlawutzie.png
assets/SchlauWutzie_KI_AI_Datacenter_Intro_V4_FINAL.mp4
```

## Build

Die GitHub Action erzeugt:

```text
SchlauWutzie_V21_8_SYSTEM_SPEECH_DEUTSCHE_AUTO_UNTERTITEL.exe
```

## Hinweis

Die V21.8 verwendet **kein faster-whisper und kein CTranslate2** für die Auto-Untertitel.

Die Untertitel-Funktion basiert auf der in Windows verfügbaren deutschen Spracherkennung.
