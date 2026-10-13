"""Bring Outlook's Calendar view to focus and step the visible week
forward/back.

Week navigation clicks the calendar's own "next/previous week" buttons via
UIA rather than sending a keyboard shortcut: new Outlook has no dedicated
next/previous-period hotkey (Alt+Right/Alt+Left just expand the ribbon
instead - confirmed live), so the button click is the only reliable way to
drive this. Their accessible name embeds the target date range (e.g. "Go to
next week September 28 - October 2, 2026 (Week 40)"), which changes every
week, so they're matched with title_re on the stable "Go to next/previous
week" prefix instead of an exact title."""

import automation

OUTLOOK_TITLE_RE = ".*Calendar.*Outlook.*"
NEXT_WEEK_TITLE_RE = ".*Go to next week.*"
PREVIOUS_WEEK_TITLE_RE = ".*Go to previous week.*"


def outlook_next_week():
    window = automation.focus_window(OUTLOOK_TITLE_RE)
    automation.click_element(window, {"title_re": NEXT_WEEK_TITLE_RE, "control_type": "Button"})


def outlook_previous_week():
    window = automation.focus_window(OUTLOOK_TITLE_RE)
    automation.click_element(window, {"title_re": PREVIOUS_WEEK_TITLE_RE, "control_type": "Button"})
