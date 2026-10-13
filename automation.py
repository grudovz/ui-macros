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
