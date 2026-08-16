V21.7.1 FIX

Warum V21.7 beim Klick auf Auto-Untertitel schließen konnte:
faster-whisper/ctranslate2 enthält native Komponenten. Ein nativer
Fehler kann den GUI-Prozess beenden, bevor Python einen normalen
Exception-Dialog anzeigen kann.

V21.7.1:
- startet die Whisper-Transkription in einem isolierten Hilfsprozess
- GUI bleibt offen, auch wenn das native Speech-Modul fehlschlägt
- zeigt Exit-Code und Statusdatei als Fehlermeldung
- PyInstaller sammelt faster_whisper und ctranslate2 explizit ein
- V21.5/21.6 Intro, StefanM und Balkenanimation bleiben erhalten
