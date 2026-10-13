# Common commands

Run from the project root in PowerShell.

## Activate the virtual environment
```powershell
.venv\Scripts\Activate.ps1
```

## Run the macro hotkey listener
```powershell
python run.py
```

## Inspect a window's UI controls (e.g. to find the VS Code chat box criteria)
```powershell
python inspect_window.py ""
```

## List all open window titles (to find the exact text to pass above)
```powershell
python -c "from pywinauto import Desktop; [print(w.window_text()) for w in Desktop(backend='uia').windows()]"
```

## Find screen coordinates under the mouse
```powershell
python coord_finder.py
```

## Inspect just the element under the mouse (hover instead of a full dump)
```powershell
python element_finder.py
```

---
These same three (activate/run/inspect) are also available as VS Code tasks —
see the "Running via VS Code tasks" note in the project docs, or just
`Ctrl+Shift+P` -> "Tasks: Run Task".

## Autostart at logon

`start_at_logon.vbs` opens VS Code on this folder and starts `run.py` via
`pythonw.exe` — hidden, no console/taskbar window at all. Its output (hotkey
list, or any hotkey-registration error) goes to `run.log` instead, since
there's no window to read it from. A per-user Startup-folder shortcut runs it
at every logon — no admin rights needed, nothing machine-wide.

Install/reinstall the shortcut:
```powershell
powershell.exe -ExecutionPolicy Bypass -File setup_autostart.ps1
```

Remove it:
```powershell
powershell.exe -ExecutionPolicy Bypass -File setup_autostart.ps1 -Remove
```

If VS Code doesn't come up already showing the Agents panel, `ctrl+shift+5`
(`toggle_vscode_agent`) brings it forward once VS Code finishes loading.

To check it's actually running (there's no window to glance at): check
`run.log` for the hotkey list, or look for `pythonw.exe` in Task Manager.
`ctrl+shift+z` quits it same as always — hotkeys are global regardless of
window visibility.

If hidden mode ever misbehaves, run `start_at_logon.bat` directly instead —
same two steps, but with `run.py` in a normal, visible, stay-open window.
