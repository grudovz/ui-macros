"""Open the GIF tab of Microsoft Teams' Emoji/GIFs/Stickers picker in the
active chat's compose box - derived via element_finder.py (P) on the toolbar
button, then again on the GIFs tab inside the popover it opens."""

import time

import automation

TEAMS_TITLE_RE = ".*Microsoft Teams.*"

# title/control_type only - the class_name's Fluent UI/Griffel-generated
# atomic CSS classes aren't stable across app restarts or Teams updates (see
# macros/teams_scroll.py for the same reasoning).
GIF_STICKERS_BUTTON_CRITERIA = {"title": "Emoji, GIFs and Stickers", "control_type": "Button"}
GIFS_TAB_CRITERIA = {"auto_id": "unified-picker-gifs", "control_type": "TabItem"}


def open_gif_picker():
    """Click the Emoji/GIFs/Stickers button, wait for its popover to open, then
    switch to the GIFs tab. Assumes the target Teams chat is already the
    active window with its compose box visible."""
    window = automation.focus_window(TEAMS_TITLE_RE)
    automation.click_element(window, GIF_STICKERS_BUTTON_CRITERIA)
    time.sleep(1)
    automation.click_element(window, GIFS_TAB_CRITERIA)
