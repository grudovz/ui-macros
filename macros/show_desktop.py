"""Show the Windows desktop (Win+D), then bring an Outlook window to focus."""

import automation

OUTLOOK_TITLE_RE = ".*Outlook.*"


def show_desktop():
    automation.send_hotkey("win", "d")
    automation.focus_window(OUTLOOK_TITLE_RE)
