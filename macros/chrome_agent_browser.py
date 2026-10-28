"""Three separate steps for the pinned Microsoft 365 Copilot tab in Chrome,
so you can stop and read in between:
- open_agent_browser switches Chrome to that tab.
- select_agent_chatbox_browser clicks into the tab's message box, ready for
  dictation.
- agent_scroll_browser clicks into the conversation just above that box, so
  Up/Down/Page keys scroll the chat history instead.

The tab is kept pinned 4th, so Chrome's own Ctrl+4 reaches it directly - no
tab-strip lookup needed. The other two macros work on whatever tab is
showing, with no tab switch of their own: Chrome only exposes the active
tab's page content to UIA, so on a tab with no such box they raise
RuntimeError without clicking anything.

MESSAGE_BOX_CRITERIA matches the box in both of Copilot's views, chat and
Cowork, with a new chat/task or an existing one showing - in each, it's the
page's only Edit carrying the "fai-EditorInput__input" class (all four
confirmed live, 2026-10-28). That class is followed by a Griffel hash (e.g.
"r18fti29"): the first part is a fixed class name the component library
sets on purpose, like Fluent UI's "fui-" classes, while the hash changes
whenever the styles do - so only the first part is matched. The chat view's
box also has an HTML id (auto_id "m365-chat-editor-target-element"), but
Cowork's has none. Neither box can be matched by name: pywinauto's
title/title_re criteria compare against an element's rich_text, which for
an editable box is the text typed into it, not its name.
"""

import pyautogui

import automation
from macros.browser_paste import BROWSER_TITLE_RE

COPILOT_TAB_NUMBER = "4"
MESSAGE_BOX_CRITERIA = {"class_name_re": ".*fai-EditorInput__input.*", "control_type": "Edit"}

# How far above the message box's top edge agent_scroll_browser clicks, at
# the box's horizontal center - same idea as agent_chat.py's
# CHAT_SCROLL_OFFSET_Y. A fixed offset rather than a lookup, since the
# conversation has no stable element of its own to target - whatever message
# content sits there gets the click. Checked live (2026-10-28) on an existing
# chat and Cowork task: 200 clears the buttons sitting up to ~155px above the
# box, and PageUp/PageDown then scrolled the conversation. Keep it well under
# ~400 - on a new Cowork task, where the box sits highest, that far up is
# already Chrome's own toolbar.
SCROLL_OFFSET_Y = 200


def _find_message_box(window):
    box = automation.find_element(window, **MESSAGE_BOX_CRITERIA)
    if box is None:
        raise RuntimeError("Could not locate the Copilot message box - is Chrome showing the Copilot tab?")
    return box


def open_agent_browser():
    automation.focus_window(BROWSER_TITLE_RE)
    # If shift were still held from the ctrl+shift hotkey that triggered
    # this, the OS would read this as ctrl+shift+4 - run.py's toggle_chrome
    # hotkey, which would minimize Chrome instead. run.py's
    # TRIGGER_RELEASE_GRACE makes that unlikely; suspect it first if this
    # ever does that.
    automation.send_hotkey("ctrl", COPILOT_TAB_NUMBER)


def select_agent_chatbox_browser():
    window = automation.focus_window(BROWSER_TITLE_RE)
    _find_message_box(window).click_input()


def agent_scroll_browser():
    window = automation.focus_window(BROWSER_TITLE_RE)
    rect = _find_message_box(window).rectangle()
    pyautogui.click((rect.left + rect.right) // 2, rect.top - SCROLL_OFFSET_Y)
