"""Focus the browser, open a fresh tab, and navigate to a URL by pasting it
into the address bar - reusable building block for any macro that needs
Chrome on a specific page (bookmarked pages, internal tools, ...) without
clicking through bookmarks/menus to get there, and without disturbing
whatever tab was already open/active.

ADDRESS_BAR_CRITERIA's auto_id was found by enumerating Edit descendants of
the focused Chrome window (Desktop(backend="uia").window(...).descendants(
control_type="Edit")) - Chrome's UIA tree doesn't expose an "omnibox" auto_id
despite that being the element's internal/DevTools name, so don't guess it
from Chromium source naming. Re-run the same enumeration if this ever stops
matching (e.g. after a Chrome update changes its UIA tree).
"""

import automation

BROWSER_TITLE_RE = ".*Google Chrome.*"
ADDRESS_BAR_CRITERIA = {"control_type": "Edit", "auto_id": "view_1012"}


def open_url(url):
    window = automation.focus_window(BROWSER_TITLE_RE)
    automation.send_hotkey("ctrl", "t")
    automation.click_element(window, ADDRESS_BAR_CRITERIA)
    automation.paste_text(url)
    automation.press_key("enter")