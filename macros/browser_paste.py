"""Focus the browser, paste a URL into the address bar, navigate, then paste
text into the first text field on the resulting page.

ADDRESS_BAR_CRITERIA and FIRST_TEXT_FIELD_CRITERIA are placeholders - run
`python inspect_window.py "Google Chrome"` to find the address bar's real
auto_id, and inspect the target page for its first text field.

Note: Chrome exposes rendered page content over UIA too, but it's less
stable than native app controls - dynamic pages can restructure their
accessibility tree on every navigation. If FIRST_TEXT_FIELD_CRITERIA stops
matching after a site update, fall back to an image template or fixed
coords for that step (see automation.click_element).
"""

import automation

BROWSER_TITLE_RE = ".*Google Chrome.*"
ADDRESS_BAR_CRITERIA = {"control_type": "Edit", "auto_id": "omnibox"}
FIRST_TEXT_FIELD_CRITERIA = {"control_type": "Edit"}


def paste_url_and_text(url, text):
    window = automation.focus_window(BROWSER_TITLE_RE)
    automation.click_element(window, ADDRESS_BAR_CRITERIA)
    automation.paste_text(url)
    automation.press_key("enter")

    window = automation.focus_window(BROWSER_TITLE_RE)  # re-fetch after navigation
    automation.click_element(window, FIRST_TEXT_FIELD_CRITERIA)
    automation.paste_text(text)
