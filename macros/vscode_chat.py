"""Cut the current selection (e.g. in Notepad/WordPad), switch to VS Code,
and paste it into the chat box.

CHAT_BOX_CRITERIA is a placeholder - run
`python inspect_window.py "Visual Studio Code"` once, find the chat input's
real control_type/title/auto_id in the output, and update it below.
"""

import automation

VSCODE_TITLE_RE = ".*Visual Studio Code.*"
CHAT_BOX_CRITERIA = {"control_type": "Edit", "title": "Chat"}


def paste_to_vscode_chat(prefix=None):
    cut_text = automation.cut_selected_text()
    window = automation.focus_window(VSCODE_TITLE_RE)
    automation.click_element(window, CHAT_BOX_CRITERIA)
    automation.paste_text((prefix or "") + cut_text)


def paste_to_vscode_chat_and_create():
    """Same as paste_to_vscode_chat, but prefixes the pasted text with
    '/create ' and submits it, to invoke the JIRA tool's /create skill."""
    paste_to_vscode_chat(prefix="/create ")
    automation.press_key("enter")
