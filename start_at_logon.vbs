' Hidden logon launcher - the Startup-folder shortcut points here instead of
' at start_at_logon.bat, so nothing shows up as a window or taskbar entry.
' Opens VS Code on this folder, then starts run.py via pythonw.exe (the
' console-free Python interpreter: plain python.exe launched this same hidden
' way still has no real console attached, and its print() calls would crash
' outright since sys.stdout becomes None with no console and no redirection)
' with output redirected to run.log, since there's no window left to read it
' from otherwise.
'
' "-u": Python fully buffers stdout/stderr when redirected to a file (only a
' real console gets line buffering), so without this flag run.log stays
' empty for the entire session - nothing is actually flushed to disk until
' the process exits - making it useless as a live diagnostic (confirmed
' live: an unbuffered run sat for minutes with a fully-registered hotkey
' listener and an empty log file).
'
' If hidden mode ever misbehaves, run start_at_logon.bat directly instead -
' same two steps, but with run.py in a normal, visible, stay-open window.
Q = Chr(34)

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)

pythonw = folder & "\.venv\Scripts\pythonw.exe"
runPy   = folder & "\run.py"
logFile = folder & "\run.log"

shell.Run "cmd /c code " & Q & folder & Q, 0, False

runCmd = Q & pythonw & Q & " -u " & Q & runPy & Q & " > " & Q & logFile & Q & " 2>&1"
shell.Run "cmd /c " & Q & runCmd & Q, 0, False
