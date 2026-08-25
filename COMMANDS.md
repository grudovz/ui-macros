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
