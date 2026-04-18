# Darts Counter

A Python darts scoring app with both CLI and desktop UI modes.

It supports multiplayer matches, common 01 game modes, legs/sets formats, checkout hints, and match statistics.

## Warning

This project is mostly vibe-coded. Expect rapid iterations, rough edges, and occasional weirdness.

## Features

- Multiple players
- Game modes: 101, 301, 501, 701, or custom start score
- Game variants: X01 and Cricket
- Match formats with legs and sets
- Bust rules and legal checkout validation
- Checkout suggestions from `checkout.json`
- End-of-match statistics (average, 3-dart average, highest score, highest checkout)
- Persistent match history (SQLite) with in-app selection and stats view
- Match history tools: search by player, export to JSON/CSV, delete saved matches
- Dedicated in-app Database Manager page with multi-select and select-all delete
- Modern desktop UI built with CustomTkinter
- Optional per-dart numpad input (with undo/clear)
- Cricket can be entered either as comma-separated hits or one dart at a time
- Live dashboard cards, timeline, and active-player transition animation

## Requirements

- Python 3.10+
- Tk runtime libraries installed on your system (required by CustomTkinter)

## Installation

### 1) Clone the project

```bash
git clone https://github.com/algardsbu/darts_counter.git
cd darts_counter
```

### 2) Install system Tk libraries

Install the package for your distro:

- Ubuntu/Debian:

  ```bash
  sudo apt update && sudo apt install -y python3-tk tk8.6
  ```

- Arch/Manjaro:

  ```bash
  sudo pacman -S tk
  ```

- Fedora:

  ```bash
  sudo dnf install -y python3-tkinter tk
  ```

- openSUSE:

  ```bash
  sudo zypper install python3-tk tk
  ```

### 3) Install Python dependency

```bash
pip install customtkinter
```

## Run

### CLI mode

```bash
python darts_counter.py
```

### UI mode

```bash
python darts_counter_ui.py
```

## Quick Usage (UI)

1. Enter player names in Player 1 and Player 2 fields.
2. Toggle "Add more than 2 players" if needed.
3. Select start score and match format.
4. Click `Start Match`.
5. Enter score by:
   - total 3-dart score, or
   - per-dart mode using the numpad.
6. Confirm checkout dart count when prompted.
7. View final stats on the in-app statistics screen.

## Project Files

- `darts_counter.py` - core CLI app and rules logic
- `darts_counter_ui.py` - CustomTkinter desktop UI
- `match_history.py` - SQLite storage for saved match history
- `checkout.json` - checkout chart used for suggestions
- `match_history.sqlite3` - auto-created local history database

## Notes

- If `python -m tkinter` fails, your Python/Tk setup is incomplete.
- Checkout suggestions are intentionally based on the included `checkout.json` data.

## Known Limitations

- Per-dart numpad multiplier (`x2`/`x3`) applies to numeric keypad dart entry only; manually typed dart values are taken as final values.
- Checkout suggestions only appear for scores present in `checkout.json`.
- Match history search is currently player-name based.
