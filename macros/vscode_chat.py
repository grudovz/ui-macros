"""Cut the current selection (e.g. in Notepad/WordPad), switch to VS Code,
and paste it into the chat box.

CHAT_BOX_CRITERIA is a chain of nested criteria (see automation.find_element_chain):
the chat panel's monaco-editor input has no title/auto_id of its own and shares
its class_name with every other editor instance in the window, so it's scoped
through the sessions panel and the currently-active session tab first. Found via
`python element_finder.py` (hover + press P for the ancestor chain).
"""

import automation

VSCODE_TITLE_RE = ".*Agents.*"
CHAT_BOX_CRITERIA = [
    {"auto_id": "workbench.parts.sessions"},
    {"control_type": "Group", "class_name_re": ".*is-active.*"},
    {"control_type": "Text", "class_name_re": ".*monaco-editor.*"},
]


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
