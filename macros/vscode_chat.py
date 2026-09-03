"""Switch to VS Code and click into its Agent Sessions chat panel: agent_chat
and agent_text target the chat's input box (ready for a subsequent paste),
agent_scroll targets the response/conversation pane above it instead.

The chat panel's monaco-editor input has no title/auto_id of its own and
shares its class_name with every other editor instance in the window, so a
single-criteria lookup can't tell chat boxes apart from each other. This used
to be scoped via a fixed child_window() chain (sessions panel -> "is-active"
Group -> monaco-editor Text), found with `python element_finder.py` (hover +
press P). That worked with one chat pane open, but broke with the VS Code
"Agent Sessions" panel showing two chat panes side-by-side (split view,
still one top-level window): only ONE monaco-editor Text descendant exists
in the whole sessions panel at any given moment - whichever pane last had
real keyboard focus, marked by a "focused" token in its class_name - and the
fixed chain's "is-active" Group step doesn't reliably scope down to just
that one pane's editor, so child_window() either matched nothing or raised
ElementAmbiguousError, which automation.find_element_chain's broad
`except Exception: return None` silently swallows into a "not found"
no-op (confirmed live: production code succeeded in one read-only test but
the user's real hotkey-triggered runs still failed to click anything).

_find_chat_box works around this without touching automation.py's shared
helpers: it enumerates every monaco-editor Text descendant under the
sessions panel directly (no exception-swallowing chain), and picks among
them explicitly instead of relying on child_window()'s implicit uniqueness
assumption.

With 2+ panes open, the "focused" class token turns out to be unreliable
too: it only marks a pane once something inside it has real OS keyboard
focus, which is normally gone by the time a hotkey fires from some other
app (confirmed live: with a genuine 2-pane split open and neither pane
freshly clicked, UIA's own HasKeyboardFocus property read False for BOTH
panes' Edit controls - there is no UIA signal at all for "which pane you
mean" in that state). Rather than fail outright, this falls back to the
rightmost pane - VS Code lays out newly-opened chats to the right, so this
is a "most likely the one you just opened" guess, not a certainty. It can
guess wrong if you actually wanted an older, further-left pane.
"""

import pyautogui

import automation

VSCODE_TITLE_RE = ".*Agents.*"
SESSIONS_PANEL_CRITERIA = {"auto_id": "workbench.parts.sessions"}

# How far above the chat box's top edge to click for agent_scroll - lands in
# the scrollable response/conversation area instead of the input box itself.
# A fixed pixel offset rather than a UIA lookup, since the response pane has
# no stable element of its own to target (same "no title/auto_id, shared
# class_name" problem as the chat box, but nested inside content that
# changes with every message).
CHAT_SCROLL_OFFSET_Y = 300


def _find_chat_box(window):
    """Return the chat box's monaco-editor Text element, or None if none
    exist. With one chat pane open there's exactly one candidate. With
    multiple panes open side-by-side: prefer the one whose class_name
    carries VS Code's "focused" token (the pane last typed into) if exactly
    one does; otherwise fall back to the rightmost candidate (see module
    docstring - a best guess, not a certainty)."""
    sessions = automation.find_element(window, **SESSIONS_PANEL_CRITERIA)
    if sessions is None:
        return None
    candidates = [
        element for element in sessions.descendants(control_type="Text")
        if "monaco-editor" in (element.element_info.class_name or "")
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    focused = [
        element for element in candidates
        if "focused" in (element.element_info.class_name or "")
    ]
    if len(focused) == 1:
        return focused[0]
    return max(candidates, key=lambda element: element.rectangle().left)


def _resolve_chat_box(window):
    """Like _find_chat_box, but raises instead of returning None - every
    macro below needs a chat box to proceed."""
    chat_box = _find_chat_box(window)
    if chat_box is None:
        raise RuntimeError("Could not locate the VS Code chat box (no sessions panel or no chat pane open)")
    return chat_box


def agent_chat():
    """Click the VS Code chat box - a separate paste macro supplies the text."""
    window = automation.focus_window(VSCODE_TITLE_RE)
    _resolve_chat_box(window).click_input()


def agent_text():
    """Cut the current selection (e.g. in Notepad/WordPad), switch to VS Code,
    paste it into the chat box prefixed with '/create ', and submit it to
    invoke the JIRA tool's /create skill. Unlike agent_chat, this one still
    does the cut+paste itself - it needs the '/create ' prefix and Enter
    submission that a generic paste macro wouldn't provide."""
    cut_text = automation.cut_selected_text()
    window = automation.focus_window(VSCODE_TITLE_RE)
    _resolve_chat_box(window).click_input()
    automation.paste_text("/create " + cut_text)
    automation.press_key("enter")


def agent_scroll():
    """Click into the chat's response/conversation pane instead of its input
    box, so subsequent Up/Down/PageUp/PageDown voice-dictation commands
    scroll the conversation history instead of typing into the input. Same
    pane-picking as agent_chat (see _find_chat_box), just clicked
    CHAT_SCROLL_OFFSET_Y px above its top edge instead of inside it."""
    window = automation.focus_window(VSCODE_TITLE_RE)
    rect = _resolve_chat_box(window).rectangle()
    x = (rect.left + rect.right) // 2
    y = rect.top - CHAT_SCROLL_OFFSET_Y
    pyautogui.click(x, y)
