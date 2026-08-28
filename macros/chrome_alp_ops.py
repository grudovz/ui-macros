"""Open the "alp ops" page directly in Chrome via its URL, instead of
clicking through the taskbar icon and "ALP IL" bookmarks folder - Chrome is
always already running, so browser_paste.open_url's own
automation.focus_window(...) call is enough to bring it to the foreground;
there was nothing left for a taskbar click to do.

Logs in afterward by pasting credentials via keyboard only - no element
criteria needed, since the page auto-focuses the username field on load and
Tab moves to the password field. Credentials come from the ALP_USERNAME/
ALP_PASSWORD environment variables rather than a literal string in this
file - macros/*.py is git-tracked, so a real password baked in here would
land in plaintext in the repo the moment it's committed. Set both once via
Windows' System Properties > Environment Variables (or `setx ALP_USERNAME
...` from a shell) before this macro can log in.
"""

import os
import time

import automation
from macros.browser_paste import open_url

ALP_OPS_URL = "https://ui-new-uat.alp.co.il/operation"


def open_alp_ops():
    open_url(ALP_OPS_URL)
    time.sleep(2.0)  # let the login page render before typing into it
    automation.paste_text(os.environ["ALP_USERNAME"])
    automation.press_key("tab")
    automation.paste_text(os.environ["ALP_PASSWORD"])
    automation.press_key("enter")
