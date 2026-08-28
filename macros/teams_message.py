"""Focus Microsoft Teams and open its jump-to-chat search box (Ctrl+G), so a
follow-up Dragon phonetic-letter command can type a name/chat into it.

This macro only does the window-focus + Ctrl+G part - the letter-typing is
handled separately by Dragon Advanced Scripting commands, which send their
keystrokes directly rather than routing back through a hotkey."""

import time

import automation

TEAMS_TITLE_RE = ".*Microsoft Teams.*"


def open_search():
    """Focus Teams (bringing it to front, launching if needed) and open the
    Ctrl+G jump-to-chat search box."""
    automation.focus_window(TEAMS_TITLE_RE)
    automation.send_hotkey("ctrl", "g")
    time.sleep(1)
