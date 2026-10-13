"""Toggle-focus macros: bring a specific app's window to the foreground, or
minimize it if it's already active - see automation.toggle_window for the
actual behavior. Each function here just supplies the window-match criteria
for one app; title regexes are reused from the macro that already defines
them where one exists, instead of duplicating the string.

minimize_active is different: a generic, app-agnostic "turn it off" macro
that just minimizes whatever window currently has focus (see
automation.minimize_active_window), for combining with some other action
that brought a window up in the first place (e.g. agent_chat's click)
instead of matching that app again by title/class.
"""

import automation
from macros.browser_paste import BROWSER_TITLE_RE
from macros.agent_chat import VSCODE_TITLE_RE

# Outlook doesn't go through automation.toggle_window like the others: new
# Outlook's window model is UIA-flaky in ways no other app here has shown -
# its own HWND changes on its own, and it was confirmed live to hold two
# top-level windows both matching ".*Outlook.*" for a full 5s retry window
# (not just a transient race - ElementAmbiguousError never cleared). Rather
# than keep guessing at UIA-side workarounds for behavior that isn't
# reliably reproducible, this pins Outlook to a fixed taskbar slot and uses
# Windows' own native Win+<N> taskbar-slot toggle instead - it minimizes/
# restores/focuses correctly for any app without resolving a window by
# title/UIA at all, so it can't hit this bug, and it covers "whichever
# Outlook version is open" for free since it doesn't care about window
# identity, only taskbar position.
OUTLOOK_TASKBAR_SLOT = "3"

# Version number in the real title ("Amadeus Bistro Portal - 9.14.10") will
# drift with every release, so match on the stable prefix only.
BISTRO_PORTAL_TITLE_RE = ".*Amadeus Bistro Portal.*"
WORDPAD_TODO_TITLE_RE = ".*to-do list.rtf.docx.*"

# File Explorer's title depends on whichever folder is open, so it can't be
# matched by text - CabinetWClass is the stable window class for its main
# window instead. If multiple Explorer windows are open, toggle_window picks
# whichever pywinauto happens to enumerate first (same "first match" tradeoff
# already accepted for VS Code's split-pane rightmost-guess elsewhere).
FILE_EXPLORER_CLASS_NAME = "CabinetWClass"


def toggle_chrome():
    automation.toggle_window(title_re=BROWSER_TITLE_RE)


def toggle_vscode_agent():
    automation.toggle_window(title_re=VSCODE_TITLE_RE)


def toggle_wordpad_todo():
    automation.toggle_window(title_re=WORDPAD_TODO_TITLE_RE)


def toggle_bistro_portal():
    automation.toggle_window(title_re=BISTRO_PORTAL_TITLE_RE)


def toggle_outlook():
    automation.send_hotkey("win", OUTLOOK_TASKBAR_SLOT)


def toggle_file_explorer():
    automation.toggle_window(class_name=FILE_EXPLORER_CLASS_NAME)


def minimize_active():
    automation.minimize_active_window()
