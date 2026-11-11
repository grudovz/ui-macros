"""Snip the area around the mouse with Windows' own Snipping Tool:
snip_around_mouse opens its overlay (Win+Shift+S) and drags a rectangle
reaching SNIP_REACH_X pixels left and right of the mouse and SNIP_REACH_Y
pixels above and below it - cut off at the edges of the screen, taskbar
excluded - then puts the mouse back. From there, the overlay carries on
exactly as after a selection made by hand: with Quick markup on, it stays
open for markup, and nothing reaches the clipboard until you capture.
Confirmed live on the main screen, 2026-11-11, by reading where the
overlay's "OverlayFrame" element (the selected area) ended up.

The overlay (SnippingTool.exe) is one "Snipping Tool Overlay" XamlWindow per
monitor, plus a root window spanning them all - found by enumerating
top-level windows while it was open. It opened ~0.6s after Win+Shift+S,
without ever taking the foreground, so it's looked up by title. Win+Shift+S
itself has to go out via automation.send_hotkey_raw - see its docstring.

The mode dropdown on the overlay's toolbar (MODE_BOX_AUTO_ID, from
enumerating the overlay's descendants) is set back to Rectangle if another
mode is showing, since dragging in any other mode would snip something else.
Just a guard: in live tests the overlay always reopened in Rectangle mode,
even right after Window mode was picked.

The drag starts in the rectangle's bottom-right corner, SNIP_REACH_Y below
the mouse: the toolbar sits at the top center of the screen, and a drag
starting on it could click it instead. Ending on it is fine (tested live).
"""

import time

import win32api
import win32con
from pywinauto import Desktop

import automation

OVERLAY_TITLE = "Snipping Tool Overlay"
OVERLAY_CLASS = "XamlWindow"
MODE_BOX_AUTO_ID = "SnippingModeComboBox"
RECTANGLE_MODE = "Rectangle"
# Well above the ~0.6s the overlay took to open in live tests.
OVERLAY_TIMEOUT = 5

# How far the snip reaches from the mouse, in screen pixels: left and right,
# and up and down - so 1200 x 1200 pixels away from the screen edges. The
# main screen is scaled to 125%, so 600 here is 480 of Windows' scaled pixels.
SNIP_REACH_X = 600
SNIP_REACH_Y = 600


def _find_mode_box():
    deadline = time.time() + OVERLAY_TIMEOUT
    while time.time() < deadline:
        for window in Desktop(backend="uia").windows(title=OVERLAY_TITLE, class_name=OVERLAY_CLASS):
            for box in window.descendants(control_type="ComboBox"):
                if box.element_info.automation_id == MODE_BOX_AUTO_ID:
                    return box
        time.sleep(0.1)
    raise RuntimeError("The snipping overlay didn't open")


def _drag_around(x, y):
    """Start and end points of a drag from the bottom-right corner to the
    top-left one of the rectangle SNIP_REACH_X/SNIP_REACH_Y around (x, y),
    cut off at the edges of its screen's work area (the screen minus the
    taskbar).

    The selection is the rectangle between the two points, with its right
    and bottom edges left out (seen live) - so the bottom-right point sits
    one pixel past the area. Except where that would be off the screen: the
    cursor can't go past its last column or row, so a snip touching that
    edge leaves that one column or row out."""
    info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONEAREST))
    work_left, work_top, work_right, work_bottom = info["Work"]
    last_column, last_row = info["Monitor"][2] - 1, info["Monitor"][3] - 1
    left = max(x - SNIP_REACH_X, work_left)
    top = max(y - SNIP_REACH_Y, work_top)
    right = min(x + SNIP_REACH_X, work_right, last_column)
    bottom = min(y + SNIP_REACH_Y, work_bottom, last_row)
    return (right, bottom), (left, top)


def snip_around_mouse():
    x, y = win32api.GetCursorPos()
    start, end = _drag_around(x, y)
    automation.send_hotkey_raw("win", "shift", "s")
    mode_box = _find_mode_box()
    if mode_box.selected_text() != RECTANGLE_MODE:
        mode_box.select(RECTANGLE_MODE)
    automation.drag(start, end)
    win32api.SetCursorPos((x, y))
