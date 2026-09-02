"""Switch to VS Code and click the chat box, ready for a subsequent paste.

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


def agent_chat():
    """Click the VS Code chat box - a separate paste macro supplies the text."""
    window = automation.focus_window(VSCODE_TITLE_RE)
    automation.click_element(window, CHAT_BOX_CRITERIA)


def agent_text():
    """Cut the current selection (e.g. in Notepad/WordPad), switch to VS Code,
    paste it into the chat box prefixed with '/create ', and submit it to
    invoke the JIRA tool's /create skill. Unlike agent_chat, this one still
    does the cut+paste itself - it needs the '/create ' prefix and Enter
    submission that a generic paste macro wouldn't provide."""
    cut_text = automation.cut_selected_text()
    window = automation.focus_window(VSCODE_TITLE_RE)
    automation.click_element(window, CHAT_BOX_CRITERIA)
    automation.paste_text("/create " + cut_text)
    automation.press_key("enter")
