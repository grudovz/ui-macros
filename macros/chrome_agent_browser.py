"""Macros for the two Microsoft 365 Copilot tabs pinned in Chrome.

The main Copilot tab gets three separate steps, so you can stop and read in
between:
- open_agent_browser switches Chrome to that tab.
- select_agent_chatbox_browser clicks into the tab's message box, ready for
  dictation.
- agent_scroll_browser clicks into the conversation just above that box, so
  Up/Down/Page keys scroll the chat history instead.

open_teams_agent_browser does the first two in one go for the other tab, the
Copilot one set up to send messages in Teams: it switches to that tab, then
clicks into its message box, ready for dictation.

The Teams tab is kept pinned 3rd and the main one 4th, so Chrome's own
Ctrl+3/Ctrl+4 reach them directly - no tab-strip lookup needed.
select_agent_chatbox_browser and agent_scroll_browser work on whatever tab
is showing, with no tab switch of their own: Chrome only exposes the active
tab's page content to UIA (both tabs', for a split view - see below), so on
a tab with no such box they raise RuntimeError without clicking anything.

The Teams tab sits in a split view beside Teams itself, on tab 2: Chrome
shows both pages at once, exposes both to UIA, and marks both tabs selected
in the tab strip. The box lookup still works there, since Teams' page has
no such box - tab 3's is the only match (confirmed live, 2026-11-11). If
Teams ever shows one too (its own Copilot pane, say), the lookup turns
ambiguous, and the macros raise RuntimeError rather than guess.

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

import time

import pyautogui

import automation
from macros.browser_paste import BROWSER_TITLE_RE

COPILOT_TAB_NUMBER = "4"
TEAMS_COPILOT_TAB_NUMBER = "3"
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

# How long open_teams_agent_browser waits after switching tabs before it
# looks for the message box. Until Chrome has switched, UIA still shows the
# tab it's leaving - and if that's the main Copilot tab, its box would be
# the one found, and the click would land where that box sits. In live
# tests (2026-11-11), UIA had already caught up by the first check, 0.1s
# after Ctrl+3, so this leaves a wide margin.
TAB_SWITCH_DELAY = 0.5

# Longer than find_element's 3s default: if Chrome has unloaded the tab in
# the background to save memory, switching to it reloads the page first, and
# the box only appears once that finishes.
TAB_LOAD_TIMEOUT = 10


def _find_message_box(window, timeout=3):
    box = automation.find_element(window, timeout=timeout, **MESSAGE_BOX_CRITERIA)
    if box is None:
        raise RuntimeError("Could not locate the Copilot message box - is Chrome showing a Copilot tab?")
    return box


def _switch_to_tab(tab_number):
    window = automation.focus_window(BROWSER_TITLE_RE)
    # If shift were still held from the ctrl+shift hotkey that triggered
    # this, the OS would read this as ctrl+shift+<digit> instead: for 4,
    # run.py's toggle_chrome hotkey, which would minimize Chrome; for 3,
    # Windows' own switch to the 3rd keyboard layout (see run.py's comment
    # on ctrl+shift digits). run.py's TRIGGER_RELEASE_GRACE makes that
    # unlikely; suspect it first if either ever happens.
    automation.send_hotkey("ctrl", tab_number)
    return window


def open_agent_browser():
    _switch_to_tab(COPILOT_TAB_NUMBER)


def select_agent_chatbox_browser():
    window = automation.focus_window(BROWSER_TITLE_RE)
    _find_message_box(window).click_input()


def agent_scroll_browser():
    window = automation.focus_window(BROWSER_TITLE_RE)
    rect = _find_message_box(window).rectangle()
    pyautogui.click((rect.left + rect.right) // 2, rect.top - SCROLL_OFFSET_Y)


def open_teams_agent_browser():
    window = _switch_to_tab(TEAMS_COPILOT_TAB_NUMBER)
    time.sleep(TAB_SWITCH_DELAY)
    _find_message_box(window, timeout=TAB_LOAD_TIMEOUT).click_input()
