"""Scroll through Microsoft Teams chat messages using arrow keys."""

import automation

TEAMS_TITLE_RE = ".*Microsoft Teams.*"


def scroll_teams(direction="down", times=5):
    automation.focus_window(TEAMS_TITLE_RE)
    automation.press_key(direction, times=times)


def scroll_teams_up(times=5):
    scroll_teams("up", times)


def scroll_teams_down(times=5):
    scroll_teams("down", times)
