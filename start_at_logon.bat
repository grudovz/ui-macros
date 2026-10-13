@echo off
rem Manual/debug variant only - the Startup shortcut runs start_at_logon.vbs
rem instead, which does the same two things hidden (no taskbar windows at
rem all). Run this one directly when you want to watch it happen live, e.g.
rem to see a hotkey-registration error as it happens instead of checking
rem run.log afterward.

rem Resolve paths relative to this script's own folder, not whatever folder
rem Explorer/Task Scheduler happens to launch it from.
cd /d "%~dp0"

rem "call", not a bare invocation: code.cmd is itself a batch file, and
rem jumping into one without "call" would hand off control permanently
rem instead of returning here to start run.py afterward.
rem The trailing "." avoids a classic argv-parsing gotcha where a quoted
rem path ending in "\" (here, %~dp0's own trailing backslash) gets its
rem closing quote treated as escaped by the spawned process's own
rem command-line parser.
call code "%~dp0."

rem New titled console, kept open (cmd /k) after run.py exits/crashes so
rem any hotkey-registration error (e.g. a stray instance from a prior
rem session still holding the hotkeys) stays visible instead of vanishing.
start "ui-macros hotkeys" cmd /k .venv\Scripts\python.exe run.py
