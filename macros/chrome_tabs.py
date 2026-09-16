"""Switch Chrome tabs using its own built-in shortcuts (Ctrl+Tab / Ctrl+Shift
+Tab) - no element criteria needed, just focus the browser window first."""

import automation
from macros.browser_paste import BROWSER_TITLE_RE


def next_tab():
    automation.focus_window(BROWSER_TITLE_RE)
    automation.send_hotkey("ctrl", "tab")


def previous_tab():
    automation.focus_window(BROWSER_TITLE_RE)
    automation.send_hotkey("ctrl", "shift", "tab")
