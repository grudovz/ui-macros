"""Entry point: registers global hotkeys for each macro and waits.

Run this once (e.g. at login), then trigger macros from any app by hotkey -
no need to switch to a terminal first, which matters since these macros are
meant to fire while some other app (Notepad, Teams) has focus.

Hotkeys are registered via the Win32 RegisterHotKey/WM_HOTKEY API (ctypes),
not the `keyboard` package. `keyboard` works by installing a global
WH_KEYBOARD_LL hook, which sits in the same OS hook chain as other programs'
hooks (e.g. the user's separate AutoHotkey script) and can suppress or delay
their key events depending on internal state that's hard to fully control
(see https://github.com/boppreh/keyboard/issues/22). RegisterHotKey is a
different mechanism entirely: the OS itself owns a central hotkey table and
posts a WM_HOTKEY message only to the registering thread when that exact
combo is pressed - it cannot see or affect any other keystroke, so it can't
interfere with AHK (or anything else) no matter what. It also can't be
mistuned into breaking itself the way `keyboard`'s suppress/trigger_on_release
options turned out to be (both tried and reverted - see project memory).
"""

import ctypes
import threading
import time
from ctypes import wintypes

import pythoncom

from macros.agent_browser import agent_browser
from macros.agent_chat_select import agent_chat_select
from macros.chrome_alp_ops import open_alp_ops
from macros.chrome_playground import open_playground
from macros.file_explorer import open_drafts
from macros.outlook_meeting import outlook_meeting
from macros.show_desktop import show_desktop
from macros.teams_gif import open_gif_picker
from macros.teams_message import open_search
from macros.teams_message_many import teams_message_many
from macros.teams_scroll import refresh_chats
from macros.vscode_chat import agent_chat, agent_scroll, agent_text

HOTKEYS = {
    # ctrl+shift+<letter> instead of ctrl+alt+<number>: on many keyboard
    # layouts, the physical AltGr key generates both ctrl and alt bits, so a
    # ctrl+alt+<key> hotkey can fire unexpectedly whenever the user just
    # types an AltGr-layout character. ctrl+shift has no such ambiguity on
    # any layout.
    #
    # Never use "x" or "v" as the letter here (or for QUIT_HOTKEY below):
    # automation.cut_selected_text()/paste_text() send synthetic ctrl+x/ctrl+v
    # respectively, and TRIGGER_RELEASE_GRACE only reduces - it doesn't
    # eliminate - the odds that one of those lands while the user's physical
    # ctrl+shift from *this* hotkey is still held, which reads to the OS as
    # ctrl+shift+x/v and fires whatever's registered on that combo (see
    # QUIT_HOTKEY's comment for how this bit run.py before). "c" is unused by
    # any macro today but would carry the same risk the moment something
    # calls automation.copy().
    "ctrl+shift+a": agent_chat,
    "ctrl+shift+b": agent_text,
    "ctrl+shift+r": agent_scroll,
    "ctrl+shift+w": agent_chat_select,
    "ctrl+shift+d": open_drafts,
    "ctrl+shift+n": outlook_meeting,
    "ctrl+shift+k": agent_browser,
    "ctrl+shift+m": refresh_chats,
    "ctrl+shift+g": open_gif_picker,
    "ctrl+shift+t": open_search,
    "ctrl+shift+u": teams_message_many,
    "ctrl+shift+o": open_alp_ops,
    "ctrl+shift+p": open_playground,
    "ctrl+shift+h": show_desktop,
}

# Avoid "x": macros/vscode_chat.py's cut_selected_text() sends a synthetic
# ctrl+x as its first action, and RegisterHotKey can't tell synthetic
# (SendInput) key events from real ones. If the user is still physically
# holding ctrl+shift from the ctrl+shift+<letter> hotkey that triggered the
# macro when that synthetic ctrl+x lands, the OS sees ctrl+shift+x and
# silently fires this quit hotkey instead - no exception, no error, the
# GetMessageW loop just breaks and the process exits (confirmed: this is why
# ctrl+shift+a intermittently made run.py "stop working" with nothing printed
# - see TRIGGER_RELEASE_GRACE below for the other half of the fix).
#
# Also avoid "q": the user's separate AutoHotkey script (default.ahk) already
# binds ctrl+shift+q (`^+q::`) - RegisterHotKey refuses to double-register a
# combo another program already owns, so this fails fast at startup rather
# than silently misbehaving, but it's still a non-starter. Check default.ahk
# before picking any other combo here.
QUIT_HOTKEY = "ctrl+shift+z"

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
# Vista+: the OS itself won't re-deliver WM_HOTKEY while the key is held,
# until it's released and pressed again - this is what stops a held key's
# autorepeat from firing the macro repeatedly, no app-side tracking needed.
MOD_NOREPEAT = 0x4000

_MODIFIER_NAMES = {"ctrl": MOD_CONTROL, "shift": MOD_SHIFT, "alt": MOD_ALT, "win": MOD_WIN}

user32 = ctypes.windll.user32


def _parse_hotkey(hotkey):
    """Parse a "ctrl+shift+a"-style string into a (modifiers, vk) pair for
    RegisterHotKey. Supports single letters and single digits only - avoid
    numpad key names ("num <digit>"): RegisterHotKey matches the literal VK
    code the keyboard driver produces, and numpad keys only produce
    VK_NUMPAD0-9 while NumLock is on; with NumLock off they produce
    navigation VK codes instead (Insert, End, arrows, ...), so a numpad
    hotkey can silently never fire depending on NumLock state (confirmed:
    this is why the quit hotkey was switched from "ctrl+shift+num 0" to a
    letter combo)."""
    *modifier_tokens, key_token = hotkey.split("+")

    modifiers = 0
    for token in modifier_tokens:
        if token not in _MODIFIER_NAMES:
            raise ValueError(f"Unknown modifier {token!r} in hotkey {hotkey!r}")
        modifiers |= _MODIFIER_NAMES[token]

    if len(key_token) == 1 and (key_token.isalpha() or key_token.isdigit()):
        vk = ord(key_token.upper())
    else:
        raise ValueError(f"Unknown key {key_token!r} in hotkey {hotkey!r}")

    return modifiers, vk


def _run_with_com(macro):
    """Run a macro on a freshly-spawned thread, joining it to a multi-threaded
    COM apartment first. pywinauto's UIA backend falls back to STA on this
    machine (see the "Revert to STA COM threading mode" warning), and calls
    made from a thread that never joined any COM apartment can block
    indefinitely waiting for STA marshaling that nothing services - forcing
    real MTA here avoids that hang entirely (confirmed empirically: identical
    calls hung forever without this, and returned promptly with it)."""
    pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
    try:
        macro()
    finally:
        pythoncom.CoUninitialize()


# WM_HOTKEY fires on key-down of the trigger combo's last key, which lands
# well before the user's fingers physically release ctrl+shift - any
# synthetic ctrl+<key> a macro sends right away can still land while those
# modifiers are physically held, making the OS see ctrl+shift+<key> and fire
# a matching registered hotkey (RegisterHotKey can't tell synthetic
# (SendInput) keys from real ones). This delay runs before every macro body
# to let the physical keys actually come up first.
TRIGGER_RELEASE_GRACE = 0.2


def run_in_background(macro):
    """Wrap a macro so the WM_HOTKEY dispatch loop returns immediately
    instead of running the macro inline (our macros wait on windows/elements
    for seconds at a time, which would otherwise stall the message loop and
    delay every other hotkey).

    Also de-dupes overlapping runs: MOD_NOREPEAT stops a held key from
    re-firing, but a fast double-press (or a slow-to-finish prior run) could
    still overlap - without this lock, overlapping runs raced each other for
    the same window's focus/UIA state, causing intermittent "Could not
    locate element" errors. The lock makes a firing that arrives while a run
    is still in flight a no-op instead."""
    lock = threading.Lock()

    def run_once():
        try:
            time.sleep(TRIGGER_RELEASE_GRACE)
            _run_with_com(macro)
        finally:
            lock.release()

    def handler():
        if lock.acquire(blocking=False):
            threading.Thread(target=run_once, daemon=True).start()
    return handler


if __name__ == "__main__":
    QUIT_ID = 0
    id_to_handler = {}

    for i, (hotkey, macro) in enumerate(HOTKEYS.items(), start=1):
        modifiers, vk = _parse_hotkey(hotkey)
        if not user32.RegisterHotKey(None, i, modifiers | MOD_NOREPEAT, vk):
            raise OSError(
                f"Could not register hotkey {hotkey!r} - it may already be bound by "
                "another program (e.g. AutoHotkey), or by another instance of this "
                "script that's still running. Pick a different combo, or close the "
                "other instance/binding, then try again."
            )
        id_to_handler[i] = run_in_background(macro)
        print(f"{hotkey} -> {getattr(macro, '__name__', 'lambda')}")

    quit_modifiers, quit_vk = _parse_hotkey(QUIT_HOTKEY)
    if not user32.RegisterHotKey(None, QUIT_ID, quit_modifiers | MOD_NOREPEAT, quit_vk):
        raise OSError(f"Could not register quit hotkey {QUIT_HOTKEY!r} - already bound elsewhere?")
    print(f"Listening for hotkeys. Press {QUIT_HOTKEY} to quit.")

    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                if msg.wParam == QUIT_ID:
                    break
                handler = id_to_handler.get(msg.wParam)
                if handler:
                    handler()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        for i in id_to_handler:
            user32.UnregisterHotKey(None, i)
        user32.UnregisterHotKey(None, QUIT_ID)
