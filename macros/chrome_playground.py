"""Open the internal "central access gateway" playground page directly in
Chrome via its URL, same pattern as macros/chrome_alp_ops.py - Chrome is
always already running, so browser_paste.open_url's own
automation.focus_window(...) call is enough to bring it to the foreground.

Logs in afterward the same way chrome_alp_ops.py does: paste username -> Tab
-> paste password -> Enter, no element criteria needed since the page
auto-focuses the username field on load. Credentials come from the
PLAYGROUND_USERNAME/PLAYGROUND_PASSWORD environment variables rather than a
literal string in this file - macros/*.py is git-tracked, so a real password
baked in here would land in plaintext in the repo the moment it's committed.
Set both once via Windows' System Properties > Environment Variables (or
`setx PLAYGROUND_USERNAME ...` from a shell) before this macro can log in.
"""

import os
import time

import automation
from macros.browser_paste import open_url

PLAYGROUND_URL = "https://central-access-gateway.k8s-uat.nes-uat-lb-internal.aah.amadeus.net/playground"


def open_playground():
    open_url(PLAYGROUND_URL)
    time.sleep(2.0)  # let the login page render before typing into it
    automation.paste_text(os.environ["PLAYGROUND_USERNAME"])
    automation.press_key("tab")
    automation.paste_text(os.environ["PLAYGROUND_PASSWORD"])
    automation.press_key("enter")
