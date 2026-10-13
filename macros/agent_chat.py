"""Switch to VS Code and click into its Agent Sessions chat panel: agent_chat
targets the chat's input box (ready for a subsequent paste), agent_text_raw
cuts the current selection and pastes it into that box (unsubmitted),
agent_scroll targets the response/conversation pane above it instead, and
agent_scroll_other does the same for whichever pane ISN'T the active one,
when 2+ chat panes are open side-by-side.

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


# Cache of the last-resolved sessions panel element, keyed by the VS Code
# window's handle - automation.find_element's wait() takes ~2s to resolve
# this panel from the top-level window every time (confirmed live: VS
# Code/Electron's UIA provider is slow at a broad search rooted at the
# whole window), which dwarfs the cost of everything else this module does
# (~0.6s to scan the panel's own descendants once you're already scoped to
# it). The cache is invalidated purely by staleness (a dead reference
# raises when queried - e.g. after the Agent Sessions view is closed and
# reopened, or VS Code restarts) or the window handle changing, never by
# which or how many panes are open: confirmed live that a single cached
# panel reference keeps returning correct, live results across both focus
# changes between panes and the pane count itself changing (tested live:
# 2 -> 3 -> 4 -> 5 panes, same reference throughout, no re-fetch needed).
_sessions_panel_cache = {}


def _sessions_panel_descendants(window):
    """Return every Text-type descendant of the sessions panel for `window`,
    reusing a cached panel reference when possible (see
    _sessions_panel_cache) instead of paying automation.find_element's ~2s
    cost on every call."""
    sessions = _sessions_panel_cache.get(window.handle)
    if sessions is not None:
        try:
            return sessions.descendants(control_type="Text")
        except Exception:
            pass

    sessions = automation.find_element(window, **SESSIONS_PANEL_CRITERIA)
    if sessions is None:
        return []
    _sessions_panel_cache[window.handle] = sessions
    return sessions.descendants(control_type="Text")


def _find_chat_box_candidates(window):
    """Return every monaco-editor Text descendant under the sessions panel -
    one per open chat pane - or [] if the panel isn't found or no pane is
    open."""
    return [
        element for element in _sessions_panel_descendants(window)
        if "monaco-editor" in (element.element_info.class_name or "")
    ]


def _pick_active(candidates):
    """Pick the pane last typed into among candidates: prefer the one whose
    class_name carries VS Code's "focused" token if exactly one does;
    otherwise fall back to the rightmost candidate (see module docstring -
    a best guess, not a certainty). Assumes candidates is non-empty."""
    if len(candidates) == 1:
        return candidates[0]
    focused = [
        element for element in candidates
        if "focused" in (element.element_info.class_name or "")
    ]
    if len(focused) == 1:
        return focused[0]
    return max(candidates, key=lambda element: element.rectangle().left)


def _find_chat_box(window):
    """Return the active chat pane's monaco-editor Text element, or None if
    no pane is open. See _pick_active for how "active" is chosen among 2+
    candidates."""
    candidates = _find_chat_box_candidates(window)
    if not candidates:
        return None
    return _pick_active(candidates)


def _find_other_chat_box(window):
    """Return a chat pane's monaco-editor Text element that ISN'T the active
    one (see _find_chat_box) - for scrolling a pane you're not typing into.
    None if there's no second pane open. With 3+ panes, picks the leftmost
    of the non-active ones - arbitrary but deterministic, same spirit as the
    rightmost-fallback rule for "active"."""
    candidates = _find_chat_box_candidates(window)
    if len(candidates) < 2:
        return None
    active = _pick_active(candidates)
    others = [element for element in candidates if element is not active]
    return min(others, key=lambda element: element.rectangle().left)


def _resolve_chat_box(window):
    """Like _find_chat_box, but raises instead of returning None - every
    macro below needs a chat box to proceed."""
    chat_box = _find_chat_box(window)
    if chat_box is None:
        raise RuntimeError("Could not locate the VS Code chat box (no sessions panel or no chat pane open)")
    return chat_box


def _resolve_other_chat_box(window):
    """Like _resolve_chat_box, but for the non-active pane - raises if
    there's no second chat pane open to target."""
    chat_box = _find_other_chat_box(window)
    if chat_box is None:
        raise RuntimeError("Could not locate a second VS Code chat pane to scroll (only one pane open?)")
    return chat_box


def agent_chat():
    """Click the VS Code chat box - a separate paste macro supplies the text."""
    window = automation.focus_window(VSCODE_TITLE_RE)
    _resolve_chat_box(window).click_input()


def agent_text_raw():
    """Cut the current selection (e.g. in Notepad/WordPad), switch to VS Code,
    and paste it into the chat box as-is, without submitting it, so you can
    review or edit it before sending it yourself."""
    cut_text = automation.cut_selected_text()
    window = automation.focus_window(VSCODE_TITLE_RE)
    _resolve_chat_box(window).click_input()
    automation.paste_text(cut_text)


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


def agent_scroll_other():
    """Like agent_scroll, but for whichever chat pane ISN'T the active one
    (see _find_other_chat_box) - lets voice-dictation scroll commands reach
    a pane you're not currently typing into, when 2+ chat panes are open
    side-by-side."""
    window = automation.focus_window(VSCODE_TITLE_RE)
    rect = _resolve_other_chat_box(window).rectangle()
    x = (rect.left + rect.right) // 2
    y = rect.top - CHAT_SCROLL_OFFSET_Y
    pyautogui.click(x, y)
