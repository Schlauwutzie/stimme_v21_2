Der Fehler 'No module named winrt.windows.foundation.collections'
kommt daher, dass das PyWinRT-Paket für Windows.Foundation.Collections
im Build fehlte. Die korrigierten Dateien enthalten dieses Paket und
nehmen das Modul zusätzlich in PyInstaller hiddenimports/collect_all auf.

Im GitHub-Projekt ersetzen:
1. requirements.txt
2. SchlauWutzie_V21_2_FINAL.spec

Danach den GitHub-Workflow erneut ausführen.
