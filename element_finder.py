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
docstring for exactly what that file looks like and its limitations. Clicks
on a generic element (no title/auto_id) also get their ancestor chain
captured automatically at that moment - the same walk the P key does - and
embedded as a comment, so a coordinate-only step already comes with what you'd
need to find a scoping ancestor, no manual re-hover afterward required.

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


def _looks_dynamic(text):
    """Weak heuristic: does `text` contain a digit? Titles like "1 running
    window pinned" or "(3) unread" encode transient state as a number - not
    every dynamic title has one (a browser's active-tab title can be entirely
    different text with no digit at all), so this only catches a subset, but
    it's cheap and catches a real class of bug seen in practice (see
    generate_macro_file()'s docstring)."""
    return any(ch.isdigit() for ch in text)


def ancestor_chain_lines(info, max_depth=15):
    """Walks `info.parent` up to `max_depth` times, closest first - the same
    walk print_ancestor_chain() (the P key) does, factored out so
    capture_click_step() can reuse it for coordinate-only recorded clicks."""
    lines = []
    depth = 0
    while info is not None and depth < max_depth:
        lines.append(f"[{depth}] {criteria_str(info)}")
        info = info.parent
        depth += 1
    return lines


def print_ancestor_chain(x, y, index):
    try:
        info = Desktop(backend="uia").from_point(x, y).element_info
    except Exception as exc:
        print(f"\n(no element here: {exc})")
        return

    header = f"{index}. ancestor chain @ (x={x}, y={y}) (closest first)"
    body_lines = [f"    {line}" for line in ancestor_chain_lines(info)]

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
    re-queried, so recording a click costs no extra UIA/COM call beyond the
    ancestor-chain walk below. Falls back to an all-None (coordinate-only)
    step if `info` is None (from_point() failed this iteration, e.g. click
    landed on a screen edge).

    When the click is coordinate-only (no title/auto_id - the case
    generate_macro_file() can't turn into a safe UIA criteria), also walks
    the ancestor chain right then, same as pressing P would - so the
    generated macro can embed it as a comment instead of requiring a manual
    re-hover+P session afterward to find a scoping ancestor."""
    fields = element_fields(info) if info is not None else {
        "title": None, "control_type": None, "auto_id": None, "class_name": None,
    }
    ancestor_chain = None
    if info is not None and not fields["title"] and not fields["auto_id"]:
        ancestor_chain = ancestor_chain_lines(info)
    return {"index": step_num, "x": x, "y": y, "ancestor_chain": ancestor_chain, **fields}


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

    Coordinate-only steps also get their ancestor chain (captured at record
    time by capture_click_step(), same walk as the P key) embedded as extra
    comment lines above the pyautogui.click(...) call, so scoping a real
    criteria later doesn't require re-hovering the same spot in a fresh
    element_finder.py session.

    Every emitted window-title regex (the module-level WINDOW_TITLE_RE and
    any mid-macro automation.focus_window(...) call inserted when a step's
    window changes) gets an inline warning comment: these are captured
    verbatim from whatever the target app's title happened to be at record
    time, which silently breaks if that app was already running in different
    state (a browser on some other tab, a taskbar icon whose tooltip encodes
    a running-window count, ...) whenever the macro replays for real - a real
    recorded macro broke exactly this way in practice. Per-step UIA criteria
    get the same treatment when the title looks digit-bearing
    (_looks_dynamic()) and auto_id is also present, since then title is
    probably safe to drop rather than fix.
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
        "  DPI/resolution. Each such step's ancestor chain was captured automatically",
        "  at record time (same walk as element_finder.py's P key) and is embedded",
        "  as a comment above the click - look there for a parent with a unique",
        "  auto_id to build a real criteria and replace the pyautogui.click(...) call.",
        f"  Coordinate-only steps: {coordinate_only_indices}" if coordinate_only_indices else "  (none in this recording)",
        "",
        "WINDOW_TITLE_RE (and any mid-macro automation.focus_window(...) call) was",
        "derived from the exact window title captured at record time - if this app",
        "might already be running in different state (another tab/file active, a",
        "taskbar tooltip's running-window count, ...) whenever this macro replays,",
        "that literal title may never match again. Each occurrence has its own",
        "inline warning comment right above it - check those before trusting a match",
        "long-term, and trim/broaden as needed the same way other macros/*.py files do.",
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
    lines.append("# Captured verbatim at record time - if this app might already be running")
    lines.append("# (in different state: another tab/file active, a taskbar tooltip's running-")
    lines.append("# window count, ...) whenever this macro replays, this exact title may never")
    lines.append("# match again. Broaden or trim it (e.g. to a stable suffix) before trusting.")
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
            lines.append("    # captured verbatim at record time - same caveat as WINDOW_TITLE_RE above")
            lines.append(f"    window = automation.focus_window({step_title_re!r})")

        if step["elapsed"] is not None:
            sleep_s = min(step["elapsed"], MAX_STEP_SLEEP)
            lines.append(f"    time.sleep({sleep_s:.3f})  # raw recorded gap: {step['elapsed']:.3f}s")

        comment_bits = [f'{k}="{step[k]}"' for k in ("title", "control_type", "auto_id", "class_name") if step[k]]
        comment = " ".join(comment_bits) if comment_bits else "(no identifying info)"

        if step["title"] or step["auto_id"]:
            criteria = {k: step[k] for k in ("control_type", "title", "auto_id") if step[k]}
            lines.append(f"    # Step {step['index']}: {comment} (x={step['x']}, y={step['y']})")
            if step["title"] and step["auto_id"] and _looks_dynamic(step["title"]):
                lines.append("    # NOTE: title contains a digit - it may encode transient state (a count,")
                lines.append("    # index, ...) that changes between runs. auto_id is also present, so")
                lines.append("    # consider dropping \"title\" from the criteria dict below if this step")
                lines.append("    # ever stops matching.")
            lines.append(f"    automation.click_element(window, {criteria!r}, coords=({step['x']}, {step['y']}))")
        else:
            lines.append(f"    # Step {step['index']}: COORDINATE-ONLY - no title/auto_id at record time")
            lines.append(f"    # captured element: {comment} (x={step['x']}, y={step['y']})")
            if step["ancestor_chain"]:
                lines.append("    # ancestor chain (closest first), captured automatically at record time -")
                lines.append("    # look for a parent with a unique auto_id to build a real criteria and")
                lines.append("    # replace the pyautogui.click(...) below with automation.click_element(...):")
                for chain_line in step["ancestor_chain"]:
                    lines.append(f"    #   {chain_line}")
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
                chain_note = " (coordinate-only - ancestor chain captured)" if step["ancestor_chain"] else ""
                print(f"\n[recorded step {step['index']}] (x={x}, y={y}) {hover_line}{chain_note}\n")
            lbutton_was_down = lbutton_is_down

        print(f"{hover_line:<140}", end="\r")
        time.sleep(0.01)

    if recording and recorded_steps:
        path = generate_macro_file(recorded_steps, record_window_title)
        print(f"\n--- ESC while recording - saved {len(recorded_steps)} step(s) -> {path} ---")
    print("\nDone.")
