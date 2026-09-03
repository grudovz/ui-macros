"""Open Microsoft 365 Copilot Chat in Chrome, same pattern as
macros/chrome_playground.py - Chrome is always already running, so
browser_paste.open_url's own automation.focus_window(...) call is enough to
bring it to the foreground.
"""

from macros.browser_paste import open_url

COPILOT_CHAT_URL = (
    "https://m365.cloud.microsoft/chat?fromcode=cmm4f10d4lc&ct=MCM_landing"
    "&ocid=MCM_landing&utm_campaign=MCM_landing&utm_source=unauth_MCM"
    "&redirfrom=CsrToSSR&from=PopupBlocked&IdentityProvider=aad&es=SSR"
)


def agent_browser():
    open_url(COPILOT_CHAT_URL)
