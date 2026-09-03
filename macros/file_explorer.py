"""Focus or open a File Explorer window at the JIRA tool's drafts folder.

Launching explorer.exe with a path that's already open in some window
brings that window to the foreground instead of opening a duplicate, so
this doesn't need any of automation.py's window-lookup/focus logic - unlike
every other macro in this project.
"""

import subprocess

DRAFTS_PATH = r"C:\Users\zgrudov\OneDrive - Amadeus Workplace\Desktop\projects\jira-tool\test 1\drafts"


def open_drafts():
    subprocess.run(["explorer.exe", DRAFTS_PATH])
