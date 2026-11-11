"""Core automation helpers: window focus/resize, UIA element lookup with
image-match and fixed-coordinate fallbacks, clipboard, and hotkeys.

Element lookup always tries these strategies in order, so macros stay
resolution/DPI independent whenever possible:
  1. UIA element lookup (by name/control_type/auto_id) - survives layout changes
  2. Image match against a template screenshot - semi-robust to layout changes
  3. Fixed screen coordinates - last resort, breaks if the layout changes
"""

import ctypes
import time
from ctypes import wintypes

import pyautogui
import pyperclip
from pywinauto import Desktop
from pywinauto.findwindows import ElementAmbiguousError, ElementNotFoundError

pyautogui.FAILSAFE = True


def minimize_active_window():
    """Minimize whatever window currently has focus, without resizing it -
    a generic "turn it off" counterpart to toggle_window's per-app matching,
    for macros that want to combine bringing a window up (e.g. agent_chat's
    click) with putting it away again afterwards, without needing to know
    which app it was.

    Operates on the raw foreground HWND (GetForegroundWindow) directly, not
    a UIA-resolved window by title/class - so unlike toggle_window, there's
    no criteria to match and nothing that can raise ElementNotFoundError or
    ElementAmbiguousError (the bug new Outlook's window model hit there).

    Minimizing (unlike restoring - see toggle_window's SW_RESTORE note)
    never actually loses a window's maximized state: Windows remembers a
    window's placement for the next restore regardless of how it was
    minimized, so a raw ShowWindow(SW_MINIMIZE) here is just as safe as
    toggle_window's own window.minimize() call."""
    SW_MINIMIZE = 6
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)


def toggle_window(timeout=5, **criteria):
    """Find a top-level window matching `criteria` (e.g. title_re=... , or
    class_name=... for windows whose title varies too much to match by text,
    like File Explorer) and toggle it exactly like Windows' own
    Win+<taskbar-slot-number> shortcut does: bring it to the foreground, or
    minimize it if it's already the active window - just driven by a window
    match instead of taskbar position, so it isn't limited to the taskbar's
    9 pinned slots or broken by their ordering.

    Unlike focus_window, this does NOT unconditionally raise the window -
    existing macros (agent_chat, agent_scroll, open_url, ...) rely on
    focus_window always bringing their target forward, so this is a
    separate function rather than a change to that one.

    "Already active" is checked via the raw Win32 foreground-window handle
    (GetForegroundWindow), not pywinauto's own is_active()/UIA-focus-based
    check - this project has been burned before by UIA's own focus signals
    going stale/unreliable in ways a direct HWND comparison isn't (see
    macros/agent_chat.py's module docstring).

    Un-minimizing uses raw ShowWindow(SW_RESTORE), not pywinauto's own
    window.restore(): that calls UIA's SetWindowVisualState(Normal), which
    unconditionally un-maximizes too - so a window that was maximized before
    being minimized (e.g. via Win+D) would come back at its small "restored"
    size instead of maximized. SW_RESTORE is what a taskbar-icon click uses
    and honors whatever state Windows itself remembers.

    Also retries on ElementAmbiguousError, not just ElementNotFoundError: new
    Outlook ("Outlook Host") briefly holds two top-level windows matching the
    same title_re while it tears down and recreates its own window during a
    restore (confirmed live - its HWND actually changes across a toggle), so
    a match can be transiently ambiguous for a moment before settling back to
    one. Treating that the same as "not found yet" and retrying is enough -
    confirmed live this clears within the timeout."""
    SW_RESTORE = 9
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            window = Desktop(backend="uia").window(visible_only=False, **criteria)
            is_foreground = ctypes.windll.user32.GetForegroundWindow() == window.handle
            if is_foreground and not window.is_minimized():
                window.minimize()
            else:
                if window.is_minimized():
                    ctypes.windll.user32.ShowWindow(window.handle, SW_RESTORE)
                window.set_focus()
            return window
        except (ElementNotFoundError, ElementAmbiguousError) as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"No unambiguous window matching {criteria!r} found") from last_error


def focus_window(title_re, timeout=5):
    """Find a top-level window whose title matches `title_re` (regex, case-insensitive)
    and bring it to the foreground. Returns the pywinauto window wrapper.

    visible_only=False because pywinauto's default (visible_only=True) relies on
    the UIA "visible" property, which some Electron apps (e.g. Microsoft Teams)
    report as False whenever the window isn't the current foreground/focused
    window - even though it's genuinely open and switchable. Without this, a
    background Teams window intermittently fails to resolve at all.

    Also retries on ElementAmbiguousError alongside ElementNotFoundError - see
    toggle_window's docstring for why (new Outlook's window briefly matches
    twice during its own restore/recreate transition)."""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            window = Desktop(backend="uia").window(title_re=title_re, visible_only=False)
            window.set_focus()
            return window
        except (ElementNotFoundError, ElementAmbiguousError) as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"No unambiguous window matching {title_re!r} found") from last_error


def resize_window(window, width, height):
    """Resize a window wrapper in place, keeping its current top-left corner."""
    rect = window.rectangle()
    window.move_window(x=rect.left, y=rect.top, width=width, height=height)


def find_element(window, timeout=3, **criteria):
    """Find a descendant control within `window` by UIA criteria (e.g. title=...,
    control_type="Edit", auto_id=...). Returns None instead of raising if not found."""
    try:
        element = window.child_window(**criteria)
        element.wait("exists enabled visible", timeout=timeout)
        return element
    except Exception:
        return None


def find_element_chain(window, criteria_chain, timeout=3):
    """Like find_element, but criteria_chain is a list of criteria dicts applied
    as nested child_window() scopes - e.g. [{"auto_id": "parent"}, {"control_type": "Text"}]
    finds a Text descendant of the auto_id="parent" descendant. Useful when no
    single criteria dict is unique on its own (e.g. a control_type/class_name
    shared by several sibling panels), but a stable ancestor is."""
    try:
        element = window
        for criteria in criteria_chain:
            element = element.child_window(**criteria)
        element.wait("exists enabled visible", timeout=timeout)
        return element
    except Exception:
        return None


def click_element(window, criteria, image=None, coords=None, timeout=3, offset=None):
    """Click a UI element, trying progressively less reliable strategies until
    one works. Raises RuntimeError if none succeed.

    criteria: dict of UIA lookup kwargs (e.g. {"control_type": "Edit", "title": "Chat"}),
    or a list of such dicts to be applied as a chain of nested scopes (see
    find_element_chain) when no single dict is unique on its own.
    image: path to a template screenshot for pyautogui.locateCenterOnScreen fallback
    coords: (x, y) fixed-coordinate fallback
    offset: (dx, dy) to click at (rect.left + dx, rect.top + dy) instead of the
    element's rect center. Some Electron/Chromium controls (confirmed with
    Teams' sidebar TreeItems) report a bounding rectangle whose bottom bleeds
    down across unrelated content below them, making the auto-computed center
    click land somewhere else entirely - use element_finder.py plus a
    screenshot to find a safe offset near the control's real visible label
    when this happens.
    """
    if isinstance(criteria, list):
        element = find_element_chain(window, criteria, timeout=timeout)
    else:
        element = find_element(window, timeout=timeout, **criteria)
    if element is not None:
        if offset is not None:
            rect = element.rectangle()
            pyautogui.click(rect.left + offset[0], rect.top + offset[1])
        else:
            element.click_input()
        return

    if image is not None:
        location = pyautogui.locateCenterOnScreen(image, confidence=0.8)
        if location is not None:
            pyautogui.click(location)
            return

    if coords is not None:
        pyautogui.click(*coords)
        return

    raise RuntimeError(f"Could not locate element {criteria!r} by UIA, image, or coordinates")


def cut_selected_text(settle=0.15):
    """Cut the current selection and return it as a string (empty string if
    nothing was selected). `settle` gives the OS a moment to update the
    clipboard before reading it back."""
    cut()
    time.sleep(settle)
    return pyperclip.paste()


def cut():
    pyautogui.hotkey("ctrl", "x")


def copy():
    pyautogui.hotkey("ctrl", "c")


def paste():
    pyautogui.hotkey("ctrl", "v")


def paste_text(text):
    """Paste literal `text` by placing it on the clipboard and sending Ctrl+V."""
    pyperclip.copy(text)
    paste()


def send_hotkey(*keys):
    """Send a key combination, e.g. send_hotkey('win', 'tab')."""
    pyautogui.hotkey(*keys)


def press_key(key, times=1, interval=0.05):
    """Press a single key repeatedly, e.g. press_key('down', times=5) to scroll."""
    for _ in range(times):
        pyautogui.press(key)
        time.sleep(interval)


# SendInput structures and flags, for send_hotkey_raw and drag below.
_INPUT_MOUSE = 0
_INPUT_KEYBOARD = 1
_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP = 0x0002
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
# MOVE | ABSOLUTE | VIRTUALDESK: move to absolute coordinates that span the
# whole virtual desktop (all monitors), not just the primary screen.
_MOUSEEVENTF_MOVE_ABSOLUTE = 0x0001 | 0x8000 | 0x4000


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


def _send_input(*inputs):
    array = (_INPUT * len(inputs))(*inputs)
    if ctypes.windll.user32.SendInput(len(inputs), array, ctypes.sizeof(_INPUT)) != len(inputs):
        raise OSError("SendInput was blocked by another thread")


# Virtual-key code and "extended key" flag for the named keys send_hotkey_raw
# supports besides single letters/digits. The modifiers are the left-hand
# keys a physical keyboard reports, not the generic VK_SHIFT/VK_CONTROL/
# VK_MENU that pyautogui sends.
_RAW_KEYS = {"win": (0x5B, True), "shift": (0xA0, False), "ctrl": (0xA2, False), "alt": (0xA4, False), "esc": (0x1B, False)}


def _key_input(key, up):
    if key in _RAW_KEYS:
        vk, extended = _RAW_KEYS[key]
    elif len(key) == 1 and key.isalnum():
        vk, extended = ord(key.upper()), False
    else:
        raise ValueError(f"Unknown key {key!r}")
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC
    flags = (_KEYEVENTF_KEYUP if up else 0) | (_KEYEVENTF_EXTENDEDKEY if extended else 0)
    return _INPUT(type=_INPUT_KEYBOARD, union=_INPUTUNION(ki=_KEYBDINPUT(vk, scan, flags, 0, 0)))


def send_hotkey_raw(*keys):
    """Like send_hotkey, but sent the way a physical keyboard sends it: through
    SendInput, with real scan codes and the left-hand modifier keys - for
    combos Windows ignores from send_hotkey. Confirmed live (2026-11-11):
    Win+Shift+S didn't open the snipping overlay from send_hotkey (pyautogui's
    keybd_event sends scan code 0 and the generic VK_SHIFT), but did from
    this. Win+D and Win+<digit> do work from send_hotkey (show_desktop,
    toggle_outlook). Supports single letters/digits plus "win", "shift",
    "ctrl", "alt" and "esc"."""
    downs = [_key_input(key, up=False) for key in keys]
    ups = [_key_input(key, up=True) for key in reversed(keys)]
    _send_input(*downs, *ups)


def _mouse_input(x, y, flags=0):
    left, top, width, height = (ctypes.windll.user32.GetSystemMetrics(i) for i in (76, 77, 78, 79))
    # SendInput's absolute coordinates run 0-65535 across the virtual desktop.
    # Rounded up, so that Windows rounding them back down lands on (x, y).
    dx = ((x - left) * 65536 + width - 1) // width
    dy = ((y - top) * 65536 + height - 1) // height
    mouse = _MOUSEINPUT(dx, dy, 0, _MOUSEEVENTF_MOVE_ABSOLUTE | flags, 0, 0)
    return _INPUT(type=_INPUT_MOUSE, union=_INPUTUNION(mi=mouse))


def drag(start, end, steps=20, duration=0.2):
    """Drag with the left mouse button from `start` to `end` - (x, y) screen
    coordinates, on any monitor - via SendInput: press at `start`, move there
    in `steps` even steps over `duration` seconds, release at `end`.

    Not pyautogui's dragTo, for two reasons. Its fail-safe raises whenever the
    cursor sits in a corner of the primary screen, which a drag along a screen
    edge can hit mid-drag - leaving the button held down. And its moves are
    SetCursorPos jumps, where these are real input events, the same as a
    physical mouse's. The release goes out even if a move fails, so the button
    can't be left held down either way."""
    _send_input(_mouse_input(*start, _MOUSEEVENTF_LEFTDOWN))
    try:
        for step in range(1, steps + 1):
            time.sleep(duration / steps)
            _send_input(_mouse_input(start[0] + (end[0] - start[0]) * step // steps,
                                     start[1] + (end[1] - start[1]) * step // steps))
    finally:
        _send_input(_mouse_input(*end, _MOUSEEVENTF_LEFTUP))
