"""Live UI element inspector: hover the mouse over any element to see just
that element's control_type/title/auto_id - the criteria needed for
automation.click_element - instead of a full recursive print_control_identifiers()
dump of the whole window.

Many elements (e.g. VS Code's Monaco editor) have no title/auto_id of their
own and share a class_name with every other editor instance, so a single
element isn't always enough to build a unique criteria. Press P to print the
full ancestor chain of whatever's under the mouse, so you can find a parent
with a unique auto_id to scope the search with.

Both P (ancestor chain) and C (current single-line criteria) also append
their output to CAPTURE_LOG_PATH - lets you note down several elements'
identifiers across a session without having to scroll back through the
terminal to find them afterward.

Press R to toggle click-recording: while recording, every real left-click is
captured (position, element criteria, and time since the previous click) and,
when you press R again (or ESC), written out as a new macros/recorded_*.py
file with a ready-to-review replay() function - see generate_macro_file()'s
docstring for exactly what that file looks like and its limitations.

Usage: python element_finder.py
Press P to print+save the ancestor chain, C to print+save the current line,
R to toggle click-recording, ESC to stop.
"""

import ctypes
import datetime
import os
import re
import sys
import time

import keyboard
import pyautogui

from pywinauto import Desktop

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CAPTURE_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "element_finder_captures.txt")
MACROS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macros")

VK_LBUTTON = 0x01
MAX_STEP_SLEEP = 3.0  # cap on replayed inter-step pause; raw recorded gap is still shown in a comment

user32 = ctypes.windll.user32
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]


def element_fields(info):
    return {
        "title": info.name or None,
        "control_type": info.control_type or None,
        "auto_id": info.automation_id or None,
        "class_name": info.class_name or None,
    }


def criteria_str(info):
    fields = element_fields(info)
    parts = []
    if fields["title"]:
        parts.append(f'title="{fields["title"]}"')
    if fields["control_type"]:
        parts.append(f'control_type="{fields["control_type"]}"')
    if fields["auto_id"]:
        parts.append(f'auto_id="{fields["auto_id"]}"')
    if fields["class_name"]:
        parts.append(f'class_name="{fields["class_name"]}"')
    return "child_window(" + ", ".join(parts) + ")" if parts else "(no identifying info)"


def describe(x, y):
    try:
        element = Desktop(backend="uia").from_point(x, y)
    except Exception as exc:
        return f"(no element here: {exc})"
    return criteria_str(element.element_info)


def print_ancestor_chain(x, y, index):
    try:
        info = Desktop(backend="uia").from_point(x, y).element_info
    except Exception as exc:
        print(f"\n(no element here: {exc})")
        return

    header = f"{index}. ancestor chain @ (x={x}, y={y}) (closest first)"
    body_lines = []
    depth = 0
    while info is not None and depth < 15:
        body_lines.append(f"    [{depth}] {criteria_str(info)}")
        info = info.parent
        depth += 1

    print(f"\n--- {header} ---")
    for line in body_lines:
        print(line)
    print(f"--- end (saved -> {CAPTURE_LOG_PATH}) ---\n")

    with open(CAPTURE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(body_lines) + "\n")


def capture_current(x, y, index):
    line = describe(x, y)
    entry = f"{index}. (x={x}, y={y}) {line}"
    with open(CAPTURE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
    print(f"\n[captured -> {CAPTURE_LOG_PATH}] {entry}")


def is_left_button_down():
    return bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)


def capture_window_title(x, y):
    try:
        return Desktop(backend="uia").top_from_point(x, y).window_text()
    except Exception:
        return None


def capture_click_step(x, y, step_num, info):
    """Builds a step dict from `info` - the element_info already looked up
    this same loop iteration for the hover line, passed in rather than
    re-queried, so recording a click costs no extra UIA/COM call. Falls back
    to an all-None (coordinate-only) step if `info` is None (from_point()
    failed this iteration, e.g. click landed on a screen edge)."""
    fields = element_fields(info) if info is not None else {
        "title": None, "control_type": None, "auto_id": None, "class_name": None,
    }
    return {"index": step_num, "x": x, "y": y, **fields}


def generate_macro_file(steps, window_title):
    """Writes macros/recorded_<timestamp>.py from recorded click `steps`
    (each: index/x/y/elapsed/window_title/title/control_type/auto_id/class_name)
    and returns its path, or returns None (writing nothing) if `steps` is empty.

    Per step: if the clicked element had a title/auto_id, emits
    automation.click_element(window, {criteria}, coords=(x, y)) - UIA-first,
    same as every hand-written macro in this project. Otherwise (a generic
    element with no title/auto_id - e.g. a bare Pane/View) emits a direct
    pyautogui.click(x, y) instead of guessing a loose UIA criteria: a loose
    dict risks silently matching the WRONG same-class element elsewhere in
    the tree, which is worse than just not trying. class_name is shown in
    each step's comment for reference but deliberately left out of the
    emitted criteria - Electron/Fluent-UI class names are often
    session-generated and unstable across app restarts (see macros/teams_scroll.py).
    """
    if not steps:
        return None

    timestamp = datetime.datetime.now()
    filename = f"recorded_{timestamp:%Y%m%d_%H%M%S}.py"
    path = os.path.join(MACROS_DIR, filename)

    coordinate_only_indices = [s["index"] for s in steps if not s["title"] and not s["auto_id"]]
    needs_pyautogui = bool(coordinate_only_indices)
    needs_time = any(s["elapsed"] is not None for s in steps)
    title_re = ".*" + re.escape(window_title or "") + ".*"

    lines = [
        '"""Auto-recorded macro - generated by element_finder.py\'s record mode',
        f"on {timestamp:%Y-%m-%d %H:%M:%S}.",
        "",
        f"Recorded {len(steps)} click(s) in a window matching WINDOW_TITLE_RE. NOT",
        "reviewed yet - check before wiring to a hotkey in run.py:",
        "",
        "- Steps using automation.click_element(...) had a title/auto_id at record",
        "  time and go through the same UIA-first, coords-fallback path every other",
        "  macro in this project uses.",
        "- Steps calling pyautogui.click(x, y) directly are COORDINATE-ONLY: the",
        "  clicked element had no title/auto_id at record time (a generic",
        "  Pane/View-style control), so no UIA criteria was safe to guess without",
        "  risking a match on the wrong same-class element elsewhere in the tree.",
        "  These WILL break if the window moves, resizes, or renders at a different",
        "  DPI/resolution. Re-derive real criteria with element_finder.py (hover + P",
        "  for the ancestor chain) before trusting this macro.",
        f"  Coordinate-only steps: {coordinate_only_indices}" if coordinate_only_indices else "  (none in this recording)",
        "",
        "WINDOW_TITLE_RE was derived from the exact window title captured at record",
        "time - if this app's title includes dynamic content (unread counts,",
        "filenames, unsaved-change markers), trim it to a stable substring yourself,",
        "the same way other macros/*.py files do, rather than trusting an exact",
        "match long-term.",
        "",
        "Not handled by the recorder - re-record or hand-edit if any step needed one",
        "of these: right-clicks, double-clicks, drags. A double-click records as two",
        "close-together single clicks, which may not register as a real double-click",
        "to apps that check OS double-click timing. A drag records as a single click",
        "at its start point only - the drag's endpoint/motion is silently lost.",
        "",
        f"Inter-step sleeps are capped at {MAX_STEP_SLEEP}s even if the original pause",
        "was longer (see each step's comment for the raw recorded gap) - restore a",
        "longer sleep by hand if the target app genuinely needs more time to respond.",
        '"""',
        "",
    ]
    if needs_time:
        lines.append("import time")
        lines.append("")
    lines.append("import automation")
    if needs_pyautogui:
        lines.append("import pyautogui")
    lines.append("")
    lines.append(f"WINDOW_TITLE_RE = {title_re!r}")
    lines.append("")
    lines.append("")
    lines.append("def replay():")
    lines.append("    window = automation.focus_window(WINDOW_TITLE_RE)")
    lines.append("")

    current_title = window_title
    for step in steps:
        if step["window_title"] and step["window_title"] != current_title:
            current_title = step["window_title"]
            step_title_re = ".*" + re.escape(current_title) + ".*"
            lines.append(f"    window = automation.focus_window({step_title_re!r})")

        if step["elapsed"] is not None:
            sleep_s = min(step["elapsed"], MAX_STEP_SLEEP)
            lines.append(f"    time.sleep({sleep_s:.3f})  # raw recorded gap: {step['elapsed']:.3f}s")

        comment_bits = [f'{k}="{step[k]}"' for k in ("title", "control_type", "auto_id", "class_name") if step[k]]
        comment = " ".join(comment_bits) if comment_bits else "(no identifying info)"

        if step["title"] or step["auto_id"]:
            criteria = {k: step[k] for k in ("control_type", "title", "auto_id") if step[k]}
            lines.append(f"    # Step {step['index']}: {comment} (x={step['x']}, y={step['y']})")
            lines.append(f"    automation.click_element(window, {criteria!r}, coords=({step['x']}, {step['y']}))")
        else:
            lines.append(f"    # Step {step['index']}: COORDINATE-ONLY - no title/auto_id at record time")
            lines.append(f"    # captured element: {comment} (x={step['x']}, y={step['y']})")
            lines.append(f"    pyautogui.click({step['x']}, {step['y']})")
        lines.append("")

    os.makedirs(MACROS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    with open(CAPTURE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"recorded macro saved -> macros/{filename} ({len(steps)} step(s))\n")

    return path


if __name__ == "__main__":
    print("Hover over any element to see its criteria.")
    print(f"Press P to print+save the ancestor chain, C to print+save the current line ({CAPTURE_LOG_PATH}),")
    print("R to toggle click-recording (saves a macros/recorded_*.py macro), ESC to stop.\n")
    p_was_down = False
    c_was_down = False
    r_was_down = False
    lbutton_was_down = False
    capture_count = 0
    recording = False
    recorded_steps = []
    record_window_title = None
    last_click_time = None
    with open(CAPTURE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n--- session {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ---\n")
    while not keyboard.is_pressed("esc"):
        x, y = pyautogui.position()
        try:
            hover_info = Desktop(backend="uia").from_point(x, y).element_info
            hover_line = criteria_str(hover_info)
        except Exception as exc:
            hover_info = None
            hover_line = f"(no element here: {exc})"

        p_is_down = keyboard.is_pressed("p")
        if p_is_down and not p_was_down:
            capture_count += 1
            print_ancestor_chain(x, y, capture_count)
        p_was_down = p_is_down

        c_is_down = keyboard.is_pressed("c")
        if c_is_down and not c_was_down:
            capture_count += 1
            capture_current(x, y, capture_count)
        c_was_down = c_is_down

        r_is_down = keyboard.is_pressed("r")
        if r_is_down and not r_was_down:
            if not recording:
                recording = True
                recorded_steps = []
                record_window_title = None
                last_click_time = None
                print("\n--- recording started - click around, press R again to stop and save ---\n")
            else:
                recording = False
                path = generate_macro_file(recorded_steps, record_window_title)
                if path:
                    print(f"\n--- recording stopped - saved {len(recorded_steps)} step(s) -> {path} ---\n")
                else:
                    print("\n--- recording stopped - nothing captured, nothing saved ---\n")
        r_was_down = r_is_down

        if recording:
            lbutton_is_down = is_left_button_down()
            if lbutton_is_down and not lbutton_was_down:
                now = time.time()
                elapsed = None if last_click_time is None else now - last_click_time
                last_click_time = now
                clicked_window_title = capture_window_title(x, y)
                if record_window_title is None:
                    record_window_title = clicked_window_title
                step = capture_click_step(x, y, len(recorded_steps) + 1, hover_info)
                step["elapsed"] = elapsed
                step["window_title"] = clicked_window_title
                recorded_steps.append(step)
                print(f"\n[recorded step {step['index']}] (x={x}, y={y}) {hover_line}\n")
            lbutton_was_down = lbutton_is_down

        print(f"{hover_line:<140}", end="\r")
        time.sleep(0.01)

    if recording and recorded_steps:
        path = generate_macro_file(recorded_steps, record_window_title)
        print(f"\n--- ESC while recording - saved {len(recorded_steps)} step(s) -> {path} ---")
    print("\nDone.")
