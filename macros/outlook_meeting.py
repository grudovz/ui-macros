"""Bring Outlook's Calendar view to focus and start a new meeting request."""

import automation

OUTLOOK_TITLE_RE = ".*Calendar.*Outlook.*"


def outlook_meeting():
    automation.focus_window(OUTLOOK_TITLE_RE)
    automation.send_hotkey("ctrl", "n")
