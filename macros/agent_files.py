"""Show a Files tab in the VS Code Agents window's editor area: switch to it
if one is already open, otherwise click the "+" at the end of the tab row,
then "Files" in the dropdown that opens - same as doing it by mouse.

Only one Files tab can be open at a time: while one is, the dropdown leaves
"Files" out and offers just Browser and Search (confirmed live - clicking "+"
anyway left the dropdown open with nothing to pick), hence the switch.

The Agents window's own shortcut for this, Ctrl+Shift+E (shown right in that
dropdown), can't be sent instead: run.py registers ctrl+shift+e globally for
minimize_active, and RegisterHotKey can't tell synthetic keys from real ones,
so sending it would minimize the window rather than reach VS Code. Clicking
sidesteps that without moving minimize_active to another combo.

All three criteria came from enumerating the Agents window's descendants,
scoped under the editor part's auto_id since that's where they live:
- The "+" is a Button named "Add Tab" (no auto_id; its class_name is only
  codicon icon classes). It was the only one in the window with one editor
  group open - if splitting the editor area ever gives each group its own
  "+", the lookup turns ambiguous and this raises RuntimeError rather than
  guessing a group.
- The dropdown is drawn inside the window (no separate popup window), as a
  Menu whose MenuItems are named with their shortcut appended - "Files
  Ctrl+Shift+E" - so FILES_ITEM_CRITERIA matches the "Files" prefix only, in
  case that shortcut is ever rebound. No other MenuItem starts with "Files".
- The open tab is a TabItem named "Files" (no auto_id; its class_name
  carries state tokens like "active selected"). FILES_TAB_CRITERIA also
  allows the ", <state>" suffix VS Code appends to a tab's name in some
  states (seen live on another tab as "HOTKEYS.md, preview").
"""

import automation
from macros.agent_chat import VSCODE_TITLE_RE

EDITOR_PART_CRITERIA = {"auto_id": "workbench.parts.editor"}
ADD_TAB_CRITERIA = [EDITOR_PART_CRITERIA, {"control_type": "Button", "title": "Add Tab"}]
FILES_ITEM_CRITERIA = {"control_type": "MenuItem", "title_re": "Files.*"}
FILES_TAB_CRITERIA = [EDITOR_PART_CRITERIA, {"control_type": "TabItem", "title_re": "Files(, .*)?$"}]


def agent_files():
    window = automation.focus_window(VSCODE_TITLE_RE)
    files_tab = automation.find_element_chain(window, FILES_TAB_CRITERIA, timeout=0)
    if files_tab is not None:
        files_tab.click_input()
        return
    # Step 1: "+" (Add Tab) at the end of the editor area's tab row
    automation.click_element(window, ADD_TAB_CRITERIA)
    # Step 2: "Files" in the dropdown it opens
    automation.click_element(window, FILES_ITEM_CRITERIA)
