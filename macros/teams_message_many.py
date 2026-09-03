"""Focus Microsoft Teams and open a new chat, ready to add multiple
recipients (Teams' Ctrl+N opens a blank "New chat" with the To: field
focused, which accepts several names before you start typing a message)."""

import automation

TEAMS_TITLE_RE = ".*Microsoft Teams.*"


def teams_message_many():
    """Focus Teams (bringing it to front, launching if needed) and open a
    new chat via Ctrl+N."""
    automation.focus_window(TEAMS_TITLE_RE)
    automation.send_hotkey("ctrl", "n")
