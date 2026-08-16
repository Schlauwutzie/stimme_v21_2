V21.8.2 FIX

The previous runtime error was:
System.Exception: The metadata file 'System.Speech.dll' could not be found.

Cause:
PowerShell had loaded System.Speech, but Add-Type was given only the bare
file name. On some Windows environments that name is not resolved as a
reference assembly.

Fix:
The actual System.Speech assembly path is now obtained from:
[System.Speech.Recognition.SpeechRecognitionEngine].Assembly.Location
and that full path is passed to Add-Type -ReferencedAssemblies.

No Whisper/CTranslate2 is used.
