"""Switch Chrome to one of its pinned Microsoft 365 Copilot tabs, start
something new there, and click into its message box, ready for dictation:
open_cowork_browser starts a new task on the Cowork tab (for requests like
sending emails or checking calendar availability), and open_agent_browser
starts a new chat on the Copilot chat tab.

Both tabs are always kept pinned (Cowork 4th, Copilot chat 5th), so
Chrome's own Ctrl+4/Ctrl+5 shortcuts reach them directly - no tab-strip
lookup needed. These only reuse those tabs, never open new ones (unlike
open_agent_browser's earlier open_url-based version, which piled up a fresh
Copilot tab on every run). Chrome only exposes the *active* tab's page
content to UIA, so none of the page criteria below can resolve until after
the tab switch.

NEW_CHAT_CRITERIA was found by enumerating the Chrome window's descendants
for a "New chat" name with the Copilot chat tab active: the only match is a
Hyperlink in the page's left nav (under auto_id="m365-copilot-app-layout-main").
It has no auto_id of its own, and its class_name is Fluent UI/Griffel-
generated atomic CSS classes that aren't stable across app updates (see
macros/teams_scroll.py for the same reasoning), so title/control_type is the
stable match. NEW_TASK_CRITERIA is the same story on the Cowork tab, where
the only "New task" match is a MenuItem in its left nav.

CHAT_MESSAGE_BOX_CRITERIA came from the same enumeration: it's the page's
only Edit besides Chrome's own address bar, and its auto_id is the page's own
HTML id - a hand-picked name, unlike its generated class_name - so that's the
stable match. Cowork's box (named "Chat input") has no auto_id, and can't be
matched by that name either: pywinauto's title/title_re criteria compare
against an element's rich_text, which for an editable box is the text typed
into it (just a newline while it's empty), not its name (confirmed live).
Its class_name is "fai-EditorInput__input" followed by a Griffel hash (e.g.
"r18fti29"): the first part is a fixed class name the component library sets
on purpose, like Fluent UI's "fui-" classes, while the hash changes whenever
the styles do - so COWORK_MESSAGE_BOX_CRITERIA matches that part alone, and
it's again the page's only match. The Copilot chat tab's box carries the
same class, but can't be picked up instead: Chrome only exposes the active
tab's content, and the box is only looked up after "New task" - which only
the Cowork tab has - was found and clicked.

Each box needs its own click: clicking "New chat" leaves keyboard focus on
that link (the page never moves it into the box by itself), and clicking "New
task" while a new task is already showing does nothing at all - the box
isn't focused either way (both confirmed live).
"""

import re
import time

import automation
from macros.browser_paste import ADDRESS_BAR_CRITERIA, BROWSER_TITLE_RE

CHAT_TAB_NUMBER = "5"
NEW_CHAT_CRITERIA = {"title": "New chat", "control_type": "Hyperlink"}
CHAT_MESSAGE_BOX_CRITERIA = {"auto_id": "m365-chat-editor-target-element", "control_type": "Edit"}

COWORK_TAB_NUMBER = "4"
NEW_TASK_CRITERIA = {"title": "New task", "control_type": "MenuItem"}
COWORK_MESSAGE_BOX_CRITERIA = {"class_name_re": ".*fai-EditorInput__input.*", "control_type": "Edit"}

# Longer than click_element's 3s default: if Chrome has unloaded the tab in
# the background to save memory, switching to it reloads the page first, and
# "New chat"/"New task" only appears once that finishes.
TAB_LOAD_TIMEOUT = 10

# Match the address bar once a new chat/task is showing (e.g.
# "copilot.cloud.microsoft/chat?fromcode=..." or
# "copilot.cloud.microsoft/cowork?fromcode=...#/"), but not an open
# conversation's ".../chat/conversation/<id>", or an open task's URL, which
# carries on past the "#/" with the task's ids.
NEW_CHAT_URL_RE = r"/chat/?(\?|$)"
NEW_TASK_URL_RE = r"#/$"

# See _wait_for_message_box. Well above the ~0.2s the box was seen sitting
# still mid-switch on either tab (between the URL changing and the box
# starting to move, or between two of its reported positions).
SETTLE_TIME = 0.5
SETTLE_TIMEOUT = 5


def _wait_for_message_box(window, box_criteria, new_url_re):
    """Return the message box once the page has finished switching to the
    new chat/task after "New chat"/"New task" is clicked, so it gets clicked
    where it ends up.

    With a conversation or task open, the box is docked at the bottom of the
    page. Shortly after the click (about 0.6-1s for a chat, 0.3s for a task),
    the URL changes, and the box slides up to the middle of the page - and
    Chrome only reports its position a couple of times along the way, so
    clicking it any earlier can land where it used to be (all confirmed
    live). With a new chat/task already showing, nothing moves and this
    returns after SETTLE_TIME.

    The box is looked up afresh for every check rather than once up front:
    on the Cowork tab, a handle to it from before the move goes stale - other
    calls on it raise COMError, but asking it for its position still works,
    so watching that can't reveal it's stale, and click_input() on it doesn't
    fail either (all confirmed live). A fresh lookup only ever finds the box
    as it is now. The Copilot chat tab's handle survives the move, but
    there's no need to treat the tabs differently.

    Gives up after SETTLE_TIMEOUT instead of raising (e.g. if Copilot ever
    changes its URLs so new_url_re stops matching): the box then just gets
    clicked wherever it is, which is still worth a try."""
    address_bar = window.child_window(**ADDRESS_BAR_CRITERIA).wrapper_object()
    deadline = time.time() + SETTLE_TIMEOUT

    while not re.search(new_url_re, address_bar.get_value()) and time.time() < deadline:
        time.sleep(0.05)

    message_box = window.child_window(**box_criteria).wrapper_object()
    rect, still_since = message_box.rectangle(), time.time()
    while time.time() - still_since < SETTLE_TIME and time.time() < deadline:
        time.sleep(0.05)
        message_box = window.child_window(**box_criteria).wrapper_object()
        current = message_box.rectangle()
        if current != rect:
            rect, still_since = current, time.time()
    return message_box


def _open_new(tab_number, new_criteria, new_url_re, box_criteria):
    """Switch Chrome to its tab_number'th tab, click the "New chat"/"New
    task" element there, then click into the message box once the page has
    settled."""
    window = automation.focus_window(BROWSER_TITLE_RE)
    # If shift were still held from the ctrl+shift hotkey that triggered
    # this, the OS would read this as ctrl+shift+4/5 - run.py's
    # toggle_chrome/toggle_vscode_agent hotkeys, which would minimize Chrome
    # or switch to VS Code instead. run.py's TRIGGER_RELEASE_GRACE makes that
    # unlikely; suspect it first if either macro ever does that.
    automation.send_hotkey("ctrl", tab_number)
    automation.click_element(window, new_criteria, timeout=TAB_LOAD_TIMEOUT)
    # Clicked directly rather than via click_element, which would look the
    # box up all over again - its "exists enabled visible" wait alone costs
    # ~0.5s even when the element is already there (timed live).
    _wait_for_message_box(window, box_criteria, new_url_re).click_input()


def open_cowork_browser():
    _open_new(COWORK_TAB_NUMBER, NEW_TASK_CRITERIA, NEW_TASK_URL_RE, COWORK_MESSAGE_BOX_CRITERIA)


def open_agent_browser():
    _open_new(CHAT_TAB_NUMBER, NEW_CHAT_CRITERIA, NEW_CHAT_URL_RE, CHAT_MESSAGE_BOX_CRITERIA)
