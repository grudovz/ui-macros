"""Toggle-focus macros: bring a specific app's window to the foreground, or
minimize it if it's already active - see automation.toggle_window for the
actual behavior. Each function here just supplies the window-match criteria
for one app; title regexes are reused from the macro that already defines
them where one exists, instead of duplicating the string.
"""

import automation
from macros.browser_paste import BROWSER_TITLE_RE
from macros.show_desktop import OUTLOOK_TITLE_RE
from macros.vscode_chat import VSCODE_TITLE_RE

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
    automation.toggle_window(title_re=OUTLOOK_TITLE_RE)


def toggle_file_explorer():
    automation.toggle_window(class_name=FILE_EXPLORER_CLASS_NAME)
