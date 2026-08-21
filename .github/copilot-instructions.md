# Copilot Instructions — UI Macros

## Project purpose
A personal Windows desktop-automation tool: macros that click UI elements, cut/copy/paste text, focus/resize windows, and issue hotkeys across apps (VS Code, Teams, Chrome, Notepad/WordPad, etc.), triggered by global hotkey while some other app has focus.

This is a sibling project to `../Macros/test 1` (the JIRA story tool) — unrelated codebase, unrelated purpose. It grew out of `coord_finder.py`, a mouse-position probe that originally lived in that project before this one existed.

## Architecture
Three-tier fallback for locating UI elements, in `automation.py`, so macros stay resolution/DPI independent whenever possible:
1. **UIA element lookup** (`pywinauto`, backend `uia`) — by name/control_type/auto_id. Preferred; survives window resize, moved windows, different screen resolutions.
2. **Image match** (`pyautogui.locateOnScreen`) — template screenshot fallback when a control has no stable UIA identity.
3. **Fixed coordinates** — last resort, explicit per-call, not a default.

## Folder layout
```
automation.py       — core helpers: focus_window, resize_window, find_element,
                       click_element (3-tier fallback), cut/copy/paste,
                       cut_selected_text, paste_text, send_hotkey, press_key
inspect_window.py    — discovery tool: prints a window's UIA control tree so
                       real name/control_type/auto_id values can be found for
                       new macros. Usage: python inspect_window.py "<title fragment>"
macros/              — one file per macro or macro family, built on automation.py
run.py               — registers global hotkeys (via `keyboard`) mapping to macro
                       functions; run this once and trigger macros from any app
requirements.txt     — pinned dependencies
```

## Conventions
- Element criteria dicts (e.g. `CHAT_BOX_CRITERIA` in `macros/vscode_chat.py`) are placeholders until verified against the real app via `inspect_window.py` — don't assume they're correct without checking.
- Prefer UIA element lookup over image matching, and image matching over fixed coordinates — only reach for a lower tier when the one above it isn't reliable for that specific control.
- `automation.py` is the shared library — new cross-cutting helpers go there, not duplicated inside a macro file.
- Windows-only (`pywinauto`'s UIA backend requires Windows). Not intended to be cross-platform.

## Testing
No real-window automation in automated tests (can't reliably simulate Windows UIA/window focus in CI). If pure-logic helpers are added (e.g. text transforms with no UI interaction), test those with `pytest` the same way `test 1/story_parser.py` is tested.

## Environment
No secrets/API keys — everything here drives the local desktop, no external services.
