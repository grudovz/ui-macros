"""Core automation helpers: window focus/resize, UIA element lookup with
image-match and fixed-coordinate fallbacks, clipboard, and hotkeys.

Element lookup always tries these strategies in order, so macros stay
resolution/DPI independent whenever possible:
  1. UIA element lookup (by name/control_type/auto_id) - survives layout changes
  2. Image match against a template screenshot - semi-robust to layout changes
  3. Fixed screen coordinates - last resort, breaks if the layout changes
"""

import time

import pyautogui
import pyperclip
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError

pyautogui.FAILSAFE = True


def focus_window(title_re, timeout=5):
    """Find a top-level window whose title matches `title_re` (regex, case-insensitive)
    and bring it to the foreground. Returns the pywinauto window wrapper."""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            window = Desktop(backend="uia").window(title_re=title_re)
            window.set_focus()
            return window
        except ElementNotFoundError as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"No window matching {title_re!r} found") from last_error


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


def click_element(window, criteria, image=None, coords=None, timeout=3):
    """Click a UI element, trying progressively less reliable strategies until
    one works. Raises RuntimeError if none succeed.

    criteria: dict of UIA lookup kwargs, e.g. {"control_type": "Edit", "title": "Chat"}
    image: path to a template screenshot for pyautogui.locateCenterOnScreen fallback
    coords: (x, y) fixed-coordinate fallback
    """
    element = find_element(window, timeout=timeout, **criteria)
    if element is not None:
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
