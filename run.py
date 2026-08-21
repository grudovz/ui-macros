"""Entry point: registers global hotkeys for each macro and waits.

Run this once (e.g. at login), then trigger macros from any app by hotkey -
no need to switch to a terminal first, which matters since these macros are
meant to fire while some other app (Notepad, Teams) has focus.
"""

import keyboard

from macros.browser_paste import paste_url_and_text
from macros.teams_scroll import scroll_teams_down, scroll_teams_up
from macros.vscode_chat import paste_to_vscode_chat, paste_to_vscode_chat_and_create

HOTKEYS = {
    "ctrl+alt+1": paste_to_vscode_chat,
    "ctrl+alt+2": paste_to_vscode_chat_and_create,
    "ctrl+alt+up": scroll_teams_up,
    "ctrl+alt+down": scroll_teams_down,
    # example only - real macros need actual url/text, not a hardcoded sample
    "ctrl+alt+3": lambda: paste_url_and_text("https://example.com", "sample text"),
}

if __name__ == "__main__":
    for hotkey, macro in HOTKEYS.items():
        keyboard.add_hotkey(hotkey, macro)
        print(f"{hotkey} -> {getattr(macro, '__name__', 'lambda')}")
    print("Listening for hotkeys. Press Ctrl+C to quit.")
    keyboard.wait()
