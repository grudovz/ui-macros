"""Refresh the Microsoft Teams chat list by re-clicking the Chats nav item."""

import time

import automation

TEAMS_TITLE_RE = ".*Microsoft Teams.*"

# title/control_type only - the auto_id ("menur1d"-style) and most of the
# class_name are Fluent UI/Griffel-generated (useId() sequence numbers,
# atomic CSS hashes) and aren't stable across app restarts or Teams updates.
CHATS_TREEITEM_CRITERIA = {"title": "Chats", "control_type": "TreeItem"}

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