"""Click the chat-picker control at the top of VS Code's Agent Sessions
panel, to switch between chats.

No UIA criteria exists for this element: element_finder.py's ancestor
chain (hover at x=1274, y=17) showed every ancestor up to the top-level
"Agents" window is a generic, title-less Pane/View shared by countless
other panes in the window - there's no auto_id/title anywhere to scope a
child_window() lookup down to just this one control. Clicks a fixed offset
from the window's top-left corner instead - survives the window moving,
but not resizing or un-maximizing (re-run element_finder.py to recompute
CHAT_PICKER_OFFSET if this stops landing correctly).
"""

import pyautogui

import automation

VSCODE_TITLE_RE = ".*Agents.*"
CHAT_PICKER_OFFSET = (1283, 26)


def agent_chat_select():
    window = automation.focus_window(VSCODE_TITLE_RE)
    rect = window.rectangle()
    pyautogui.click(rect.left + CHAT_PICKER_OFFSET[0], rect.top + CHAT_PICKER_OFFSET[1])
