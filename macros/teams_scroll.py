"""Refresh the Microsoft Teams chat list by re-clicking the Chats nav item.

Double-clicking the Chats header also seeds keyboard focus onto the left
chat list itself - without it, Up/Down arrow presses scroll messages in the
right-hand conversation pane instead of moving between conversations. This
is now this macro's main practical use: trigger this hotkey once, then issue
Up/Down arrow-key voice-dictation commands directly to navigate between
chats (confirmed live: 5x Down after the double-click moved the active
conversation once per press)."""

import time

import automation

TEAMS_TITLE_RE = ".*Microsoft Teams.*"

# title/control_type only - the auto_id ("menur1d"-style) and most of the
# class_name are Fluent UI/Griffel-generated (useId() sequence numbers,
# atomic CSS hashes) and aren't stable across app restarts or Teams updates.
#
# title_re prefix match, not an exact title: this row's accessible name is
# hover-state-dependent - at rest it's exactly "Chats", but the moment the
# mouse is resting on it (which happens right after the first click below
# moves the cursor there), Teams appends its normally-hidden inline controls'
# labels, turning it into "Chats More section options Unread Has context
# menu". An exact title="Chats" match then fails on the second click below,
# which is the "doesn't always reliably click the second time" bug -
# confirmed live by comparing an exact match (returned None while hovered)
# against this prefix match (still found the same element) at the same
# moment. The prefix survives both name states.
CHATS_TREEITEM_CRITERIA = {"title_re": "^Chats", "control_type": "TreeItem"}

# Teams reports this TreeItem's bounding rectangle as spanning almost the
# entire remaining chat list below its header (confirmed via element_finder.py
# + a screenshot: rect.top/left/right line up with the real "Chats" label, but
# rect.bottom was ~3000px too far down) - a known Electron/Chromium UIA quirk.
# The default rect-center click therefore lands deep in the conversation list
# instead of on the header, so click near its real top-left position instead.
CHATS_TREEITEM_CLICK_OFFSET = (50, 15)


def refresh_chats():
    """Click the Chats nav item, wait a second, then click it again."""
    window = automation.focus_window(TEAMS_TITLE_RE)
    automation.click_element(window, CHATS_TREEITEM_CRITERIA, offset=CHATS_TREEITEM_CLICK_OFFSET)
    time.sleep(1)
    automation.click_element(window, CHATS_TREEITEM_CRITERIA, offset=CHATS_TREEITEM_CLICK_OFFSET)