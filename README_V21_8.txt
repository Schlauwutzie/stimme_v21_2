V21.8 – Windows System.Speech Deutsche Auto-Untertitel

Whisper/faster-whisper/CTranslate2 wurde aus dem Untertitelweg entfernt.

Die deutsche Erkennung nutzt den installierten Windows de-DE
Spracherkenner über System.Speech. Wort-Zeitstempel kommen aus
RecognizedWordUnit.AudioPosition und AudioDuration.

Der GitHub-Workflow prüft den de-DE-Recognizer vor dem Build.
Voraussetzung: Windows mit installiertem deutschem Spracherkenner.

StefanM, V21.5-K.I.-Balken, Datacenter-Intro und 9:16-Export
bleiben erhalten.
