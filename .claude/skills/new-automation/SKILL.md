---
name: new-automation
description: Use when adding a new pywinauto UI element target to a macro, wiring up a brand-new macro, or fixing/updating an existing macro's *_CRITERIA in this ui-macros project (e.g. targeting a new app, a new element, or a criteria that stopped matching). Walks through using element_finder.py to derive criteria and wiring it into the macro file.
---

# New automation / macro target

This project's macros (`macros/*.py`) locate UI elements via `automation.click_element(window, criteria)`, which accepts either a single UIA criteria dict or a list of dicts applied as nested `child_window()` scopes (`automation.find_element_chain`). Use this skill whenever the user wants to build a new macro or point an existing one at a specific on-screen element.

## Inputs the user provides

When invoking this, expect the user to give both:
1. The **element output** from `element_finder.py` (a single-line `child_window(...)` hover result, and/or an ancestor chain from pressing `P`).
2. A **description of the steps** the new automation should perform (e.g. "cut the selection, switch to app X, click field Y, paste, press enter") - use this to shape the macro function itself, not just the criteria dict. Don't assume a step sequence; go with what the user describes, and ask if it's ambiguous which element in their step description the pasted output corresponds to.

## Steps

1. From the element output, decide if a single element is unique enough, or if an ancestor needs to be used for scoping:
   - If the hovered element already has a `title` or `auto_id`, that alone is usually unique enough.
   - If it's generic (shared `control_type`+`class_name`, no `title`/`auto_id` - common for rendered web/Electron content: Chrome page content, Monaco editors, etc.), use the ancestor chain the user pasted to find the *closest* ancestor with something uniquely identifying it - a real `auto_id` is best, a distinguishing class fragment (e.g. `is-active`) is second-best. Don't reach further up than necessary.

2. Build the criteria:
   - Unique alone: a flat dict, e.g. `{"control_type": "Edit", "auto_id": "omnibox"}`.
   - Needs scoping: a list of dicts ordered outer -> inner, e.g.
     ```python
     CHAT_BOX_CRITERIA = [
         {"auto_id": "workbench.parts.sessions"},
         {"control_type": "Group", "class_name_re": ".*is-active.*"},
         {"control_type": "Text", "class_name_re": ".*monaco-editor.*"},
     ]
     ```
     Use `class_name_re`/`title_re` (regex) instead of exact `class_name`/`title` whenever the string includes state-dependent tokens (e.g. `focused`, `hovered`) that come and go.

3. Write or update the macro function in `macros/*.py` to match the user's described steps, using `automation.py`'s helpers (`focus_window`, `click_element`, `cut_selected_text`, `paste_text`, `press_key`, etc.). Set/update the `*_CRITERIA` constant(s) and `*_TITLE_RE`, and refresh the module docstring's note on how the criteria was derived (style already used in `macros/vscode_chat.py` and `macros/browser_paste.py`).

4. Double-check `*_TITLE_RE` against the real window title visible in the ancestor chain (the `title=` field on the top-level `Window`/`Pane` entries near the end of the chain) - don't assume it matches the app's marketing name (e.g. a window can be titled "Agents" rather than "Visual Studio Code").

5. Verify read-only before running anything for real: write a small throwaway script that calls `automation.focus_window(TITLE_RE)` then `automation.find_element` (flat criteria) or `automation.find_element_chain` (chained criteria) and prints what it found - no `.click_input()` - so a wrong guess doesn't cause an unwanted click/paste on the user's real desktop. Delete the throwaway script afterward.

6. To actually run/replay a macro for a real functional test (recorded via `element_finder.py`'s R key, or hand-written) - whether the user asks to "test it", "replay it", or just approves after step 5 - call its function directly rather than launching all of `run.py`: `macros/` is a real package (`macros/__init__.py` exists), so from the project root:
   ```
   ./.venv/Scripts/python.exe -c "from macros.<module> import <function>; <function>()"
   ```
   This performs real clicks against the live desktop, so warn the user first (unlike step 5, it is not read-only). A freshly click-recorded file's entry point is always named `replay()` (e.g. `from macros.recorded_20260825_160358 import replay; replay()`) - use that name until the macro is renamed per step 7.

7. Once a recorded macro is confirmed working, rename both the file and its `replay()` function to something descriptive (matching the style of e.g. `macros/teams_gif.py`'s `open_gif_picker`) before wiring it up - a `recorded_<timestamp>.py`/`replay()` name is only meant to survive until reviewed. Pull the per-step coordinates/criteria out of the generated inline comments into named `*_CRITERIA` constants and `*_TITLE_RE`, and replace the auto-generated docstring with one in the project's normal style (what it does, how/when the criteria was derived). While doing this, resolve every inline warning comment `element_finder.py` embedded (above `WINDOW_TITLE_RE`, any mid-macro `automation.focus_window(...)`, and any digit-bearing per-step `title`) rather than just deleting them - see the pitfall below on captured-at-record-time titles for what "resolve" means in each case.

   Also **keep a `# Step N: <short element description>` comment directly above each corresponding `automation.click_element(...)`/`pyautogui.click(...)` line** - the raw generated file already has one per step (auto-numbered from the recording); when rewriting into named constants, replace its raw criteria dump with a short human-readable description but keep the same step number. This is what lets the user say "insert a paste after step 3" and have it map unambiguously onto the cleaned-up file, rather than the recorder's own transient numbering - so it must survive the cleanup, not just exist in the throwaway `recorded_*.py`. If a step is later inserted/removed by hand (e.g. adding a keypress between steps 2 and 3), renumber the remaining steps to stay contiguous so references stay unambiguous.

   If the reviewed content ends up living in a separate, newly-authored file rather than an in-place rename (e.g. `macros/chrome_alp_ops.py` was written fresh rather than `recorded_20260824_181234.py` being renamed to it), **delete the original `recorded_<timestamp>.py`** once the new file is confirmed working - don't leave both around. An in-place rename makes this automatic; a separate new file does not, so check for this explicitly rather than assuming the old one is gone.

8. If it's a new macro, add it to `HOTKEYS` in `run.py`, wrapped the same way existing entries are (see pitfalls below), and pick a `ctrl+shift+<key>` combo not already in use - check both `run.py`'s existing `HOTKEYS`/`QUIT_HOTKEY` AND the user's AutoHotkey bindings (see `[[reference-ahk-hotkey-bindings]]` memory) before picking one. Two prior combos (`ctrl+shift+l`, `ctrl+shift+q`) silently collided with the AHK script and only surfaced as a `RegisterHotKey` failure or reported wrong behavior - don't guess. If `ctrl+shift+<key>` is ever tight on free letters, adding a third modifier (`ctrl+shift+win+<key>` - `_parse_hotkey` already supports any combination of `ctrl`/`shift`/`alt`/`win`) is a fine way to get more combos: these hotkeys are only ever fired by the user's pre-recorded voice-dictation macros, never typed by hand, so there's no ergonomic reason to keep them to two modifiers. Still avoid adding `alt` into that mix, though - see the `ctrl+alt`/AltGr pitfall below, which is about accidental firing during normal typing and applies regardless of how the hotkey is meant to be triggered.

9. Optionally, once wired, the user can also smoke-test the real hotkey via `python run.py` - though step 6's direct call already exercises the same macro code, this additionally confirms the hotkey itself registers and dispatches correctly.

## Known pitfalls (from prior debugging in this project)

- A single element's `control_type`+`class_name` is often shared by many sibling elements (e.g. every Monaco editor instance in a VS Code-based app) - don't treat it as unique without checking the ancestor chain first.
- `run.py` registers hotkeys via the Win32 `RegisterHotKey`/`WM_HOTKEY` API (ctypes), not the `keyboard` package - do not reintroduce `keyboard.add_hotkey`/`keyboard.wait` here. `keyboard` installs a global keyboard hook that shares the OS hook chain with other programs (e.g. the user's separate AutoHotkey script) and was confirmed, across several attempts, to intermittently suppress or corrupt AHK's own hotkeys no matter how its `suppress`/`trigger_on_release` options were tuned (see `[[project-no-suppress-hotkeys]]` memory). `RegisterHotKey` doesn't install a hook at all, so it can't interfere with anything else.
- The dispatch loop needs to return almost immediately (that's why macros run on a background thread, spawned from `run_in_background`) - with `RegisterHotKey` this is because a slow handler stalls the `GetMessage` loop and delays every other hotkey, not because of any suppression concern.
- Avoid `ctrl+alt+<key>` hotkey combos - on many keyboard layouts, the physical `AltGr` key generates both the `ctrl` and `alt` modifier bits, so a `ctrl+alt+<key>` hotkey can fire unexpectedly whenever the user just types an AltGr-layout character. Prefer `ctrl+shift+<key>`, which has no such ambiguity on any layout.
- New hotkey key names (beyond single letters/digits) need a virtual-key-code lookup added to `run.py`'s `_parse_hotkey` - it raises a clear `ValueError` for anything unmapped rather than silently mismatching. Avoid numpad key names (`num <digit>`): `RegisterHotKey` matches the literal VK code the keyboard driver produces, and numpad keys only produce `VK_NUMPAD0-9` while NumLock is on - with NumLock off they produce navigation VK codes instead, so a numpad hotkey can silently never fire depending on NumLock state (this is why the quit hotkey moved from `ctrl+shift+num 0` to `ctrl+shift+q`).
- `automation.focus_window` needs a window that's genuinely open but not currently focused (the common case when triggered by a global hotkey) to still resolve. Electron-based apps (confirmed with Microsoft Teams) can report their UIA "visible" property as False whenever they aren't the foreground window, even though they're genuinely open/switchable - `focus_window` already passes `visible_only=False` to work around this, so don't remove it, and expect the same quirk from other Electron/Chromium apps (Slack, Discord, VS Code-based tools) if a similar "window not found" bug recurs.
- Window titles and per-step `title` criteria captured by `element_finder.py`'s recorder (R key) or by hand reflect whatever state the target app happened to be in *at record time* - an already-running app's currently-active tab/file, or a taskbar tooltip's live running-window count - and can silently stop matching the moment that state differs on replay. This bit a real recorded macro (`macros/chrome_alp_ops.py`): `WINDOW_TITLE_RE` was recorded as `.*New Tab - Google Chrome.*` because Chrome happened to launch fresh during recording, then failed for real once Chrome was already open on an unrelated tab - fixed by broadening to just `.*Google Chrome.*` (Chrome's title always ends that way regardless of tab; Electron apps sharing its `Chrome_WidgetWin_1` class do NOT end their titles that way, so this still disambiguates). The recorder now emits an inline warning comment above every `WINDOW_TITLE_RE`/`focus_window(...)` call and above any per-step `title` criteria that looks digit-bearing (`_looks_dynamic()` - catches counts like "1 running window pinned", not text-only dynamic titles like an active tab name) - when reviewing a recording (step 7), actually resolve each one: broaden/trim titles to a stable substring, and drop a digit-bearing `title` in favor of `auto_id` when both are present.
- pywinauto's UIA backend falls back to STA COM threading on this machine. A thread that never joins any COM apartment can hang indefinitely making UIA calls (confirmed empirically - not just slow, genuinely stuck). `run.py`'s background-thread dispatch joins each spawned thread to a real MTA apartment (`pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)`) before running the macro, and tears it down after - keep this if you change how macros get dispatched to background threads.
