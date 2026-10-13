# Hotkeys

Everything built in this project so far: each macro's hotkey (mirrors
`run.py`'s `HOTKEYS` dict) and a one-line summary of what it does. Update this
file in the same change whenever a macro is added, removed, renamed, or
changes behavior, or a hotkey is reassigned.

## Agent / chat

Everything here drives the VS Code **Agents** window.
With 2+ chat panes open side by side, `agent_chat`, `agent_text_raw` and
`agent_scroll` pick the pane you last typed in - or the rightmost one, if VS
Code can't tell.

| Hotkey | Macro | What it does |
|---|---|---|
| `ctrl+shift+a` | `agent_chat` | Click into the chat input box, ready for a paste |
| `ctrl+shift+f` | `agent_text_raw` | Cut the selected text and paste it into the chat as-is, without sending it, so you can edit first |
| `ctrl+shift+r` | `agent_scroll` | Click into the conversation area above the input box, so Up/Down/Page keys scroll the chat history |
| `ctrl+shift+i` | `agent_scroll_other` | Like `agent_scroll`, but for the other chat pane - the one you're not typing in |
| `ctrl+shift+w` | `agent_chat_select` | Open the chat picker at the top of the Agent Sessions panel, to switch chats |

## Teams

| Hotkey | Macro | What it does |
|---|---|---|
| `ctrl+shift+m` | `refresh_chats` | Click the Chats header twice to refresh the chat list and focus it, so Up/Down move between conversations |
| `ctrl+shift+g` | `open_gif_picker` | Open the GIFs tab of the emoji/GIF/sticker picker in the current chat |
| `ctrl+shift+t` | `open_search` | Open the jump-to-chat search box (Ctrl+G), ready for a name |
| `ctrl+shift+u` | `teams_message_many` | Start a new chat (Ctrl+N) with the To: field focused, for messaging several people at once |

## Outlook

`outlook_next_week`/`outlook_previous_week` need Outlook to already be showing
the Calendar - they find the window by "Calendar" in its title.

| Hotkey | Macro | What it does |
|---|---|---|
| `alt+shift+q` | `outlook_next_week` | Show next week in the calendar |
| `alt+shift+s` | `outlook_previous_week` | Show previous week in the calendar |

## Chrome

| Hotkey | Macro | What it does |
|---|---|---|
| `ctrl+shift+k` | `open_agent_browser` | Switch to the Copilot chat tab (Ctrl+5 - keep it pinned 5th), click "New chat", then click into the message box, ready for dictation |
| `ctrl+shift+n` | `open_cowork_browser` | Switch to the Cowork tab (Ctrl+4 - keep it pinned 4th), click "New task", then click into the message box, ready for dictation (e.g. to have it send an email or check calendar availability) |
| `ctrl+shift+o` | `open_alp_ops` | Open the ALP ops page in a new tab and log in (needs `ALP_USERNAME`/`ALP_PASSWORD` env vars) |
| `ctrl+shift+p` | `open_playground` | Open the central-access-gateway playground in a new tab and log in (needs `PLAYGROUND_USERNAME`/`PLAYGROUND_PASSWORD` env vars) |
| `ctrl+shift+j` | `previous_tab` | Switch to the previous tab |
| `ctrl+shift+y` | `next_tab` | Switch to the next tab |

## Window focus / misc

"Toggle" below means: bring that app's window to the front, or minimize it if
it's already the active window - same as clicking its taskbar icon.

| Hotkey | Macro | What it does |
|---|---|---|
| `ctrl+shift+d` | `open_drafts` | Open the jira-tool drafts folder in File Explorer (reuses the window if it's already open) |
| `ctrl+shift+h` | `show_desktop` | Hide everything except Outlook (Win+D, then bring Outlook back) |
| `ctrl+shift+e` | `minimize_active` | Minimize whichever window is currently active |
| `ctrl+shift+4` | `toggle_chrome` | Toggle Chrome |
| `ctrl+shift+5` | `toggle_vscode_agent` | Toggle the VS Code Agents window |
| `ctrl+shift+6` | `toggle_wordpad_todo` | Toggle the WordPad to-do list (`to-do list.rtf.docx`) |
| `ctrl+shift+7` | `toggle_bistro_portal` | Toggle the Amadeus Bistro Portal |
| `ctrl+shift+8` | `toggle_outlook` | Toggle Outlook - via Win+3, so Outlook must stay pinned 3rd on the taskbar |
| `ctrl+shift+9` | `toggle_file_explorer` | Toggle File Explorer (whichever window is found first, if several are open) |

## Quit

| Hotkey | Action |
|---|---|
| `ctrl+shift+z` | Quit `run.py` - every hotkey above stops working until it's restarted |

## Not bound to a hotkey

| File | What it is |
|---|---|
| `macros/browser_paste.py` | `open_url(url)` - shared building block, not a macro: focus Chrome, open a new tab, paste the URL, press Enter. Used by `open_alp_ops`, `open_playground` |

## Free 2-modifier slots (as of 2026-10-13)

- `ctrl+shift`: `b`, `q`, `s`, digit `0`
- `alt+shift`: everything except `d`, `3` (AHK-owned) and `q`, `s` (used above)

Also check the user's separate AutoHotkey script (`default.ahk`) before
assigning a new combo - it claims some letter/digit combos of its own,
independent of anything in this repo.
