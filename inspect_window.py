"""One-off discovery helper: print UIA control identifiers for a window, to
find the name/control_type/auto_id values needed for automation.click_element
criteria in your own macros.

Usage: python inspect_window.py "Visual Studio Code"
(matches any window whose title contains the given text)
"""

import sys

from pywinauto import Desktop

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    title_fragment = sys.argv[1]
    window = Desktop(backend="uia").window(title_re=f".*{title_fragment}.*")
    window.print_control_identifiers()
