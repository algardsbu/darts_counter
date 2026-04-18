from __future__ import annotations

import csv
import json
from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from darts_counter import checkout_suggestions, possible_checkout_dart_counts
from match_history import delete_match, get_match, init_db, list_matches, save_match


@dataclass
class PlayerState:
    name: str
    score: int
    legs_in_set: int = 0
    legs_won: int = 0
    sets_won: int = 0
    turns_played: int = 0
    darts_thrown: int = 0
    total_scored: int = 0
    highest_score: int = 0
    highest_checkout: int = 0


class DartsUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Darts Counter")
        self.geometry("980x720")
        self.minsize(920, 680)

        self.start_score = 501
        self.legs_to_win_set = 1
        self.sets_to_win_match = 1

        self.players: list[PlayerState] = []
        self.set_number = 1
        self.leg_number = 1
        self.leg_start_player_index = 0
        self.turn_offset = 0
        self.pending_checkout_player_index: int | None = None
        self.pending_checkout_score = 0
        self.pending_valid_counts: list[int] = []

        self.mode_var = tk.StringVar(value="501")
        self.custom_score_var = tk.StringVar(value="501")
        self.preset_var = tk.StringVar(value="Single leg")
        self.custom_legs_var = tk.StringVar(value="3")
        self.custom_sets_var = tk.StringVar(value="3")
        self.more_players_var = tk.BooleanVar(value=False)
        self.player1_var = tk.StringVar(value="Player 1")
        self.player2_var = tk.StringVar(value="Player 2")

        self.current_label_var = tk.StringVar(value="Current player: -")
        self.round_label_var = tk.StringVar(value="Set 1, Leg 1")
        self.checkout_label_var = tk.StringVar(value="Checkout: -")
        self.checkout_prompt_var = tk.StringVar(value="")
        self.checkout_count_var = tk.StringVar(value="")
        self.stats_title_var = tk.StringVar(value="Match statistics")
        self.stats_subtitle_var = tk.StringVar(value="")
        self.input_mode_var = tk.StringVar(value="Total")
        self.dart_score_vars = [tk.StringVar(value=""), tk.StringVar(value=""), tk.StringVar(value="")]
        self.dart_base_inputs = ["", "", ""]
        self.per_dart_total_var = tk.StringVar(value="Per-dart total: 0")
        self.dart_multiplier_var = tk.StringVar(value="x1")
        self.history_selection_var = tk.StringVar(value="No saved matches")
        self.history_search_var = tk.StringVar(value="")

        self.extra_player_vars: list[tk.StringVar] = []
        self.extra_player_entries: list[ctk.CTkEntry] = []
        self.score_row_frames: list[ctk.CTkFrame] = []
        self.score_row_name_labels: list[ctk.CTkLabel] = []
        self.score_row_value_labels: list[tuple[ctk.CTkLabel, ctk.CTkLabel, ctk.CTkLabel]] = []
        self.dart_entries: list[ctk.CTkEntry] = []
        self.numpad_buttons: list[ctk.CTkButton] = []
        self.selected_dart_index = 0
        self.turn_animation_after_id: str | None = None
        self.history_option_to_id: dict[str, int] = {}

        self.row_normal_light = "#e5e7eb"
        self.row_normal_dark = "#1f2937"
        self.row_active_light = "#dbeafe"
        self.row_active_dark = "#1e3a8a"

        self.setup_frame = ctk.CTkFrame(self)
        self.game_frame = ctk.CTkFrame(self)
        self.stats_frame = ctk.CTkFrame(self)

        self._build_setup_ui()
        self._build_game_ui()
        self._build_stats_ui()

        init_db()
        self.refresh_history_options()

        self.setup_frame.pack(fill="both", expand=True, padx=16, pady=16)

    def _build_setup_ui(self) -> None:
        self.setup_frame.grid_columnconfigure(0, weight=1)
        self.setup_frame.grid_columnconfigure(1, weight=1)
        self.setup_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(self.setup_frame, text="Darts Counter", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 14)
        )

        ctk.CTkLabel(self.setup_frame, text="Player 1 name").grid(row=1, column=0, sticky="w", padx=16)
        self.player1_entry = ctk.CTkEntry(self.setup_frame, textvariable=self.player1_var, width=240)
        self.player1_entry.grid(row=2, column=0, sticky="w", padx=16, pady=(4, 10))

        ctk.CTkLabel(self.setup_frame, text="Player 2 name").grid(row=1, column=1, sticky="w", padx=16)
        self.player2_entry = ctk.CTkEntry(self.setup_frame, textvariable=self.player2_var, width=240)
        self.player2_entry.grid(row=2, column=1, sticky="w", padx=16, pady=(4, 10))

        self.more_players_switch = ctk.CTkSwitch(
            self.setup_frame,
            text="Add more than 2 players",
            variable=self.more_players_var,
            onvalue=True,
            offvalue=False,
            command=self._on_more_players_toggled,
        )
        self.more_players_switch.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10))

        self.more_players_frame = ctk.CTkFrame(self.setup_frame)
        self.more_players_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        self.more_players_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.more_players_frame, text="Additional players").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.more_players_entries_frame = ctk.CTkFrame(self.more_players_frame)
        self.more_players_entries_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        self.more_players_buttons_frame = ctk.CTkFrame(self.more_players_frame, fg_color="transparent")
        self.more_players_buttons_frame.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(self.more_players_buttons_frame, text="Add player field", command=self._add_extra_player_field).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(self.more_players_buttons_frame, text="Remove player field", command=self._remove_extra_player_field).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.more_players_frame.grid_remove()

        ctk.CTkLabel(self.setup_frame, text="Start score").grid(row=5, column=0, sticky="w", padx=16)
        self.mode_menu = ctk.CTkOptionMenu(
            self.setup_frame,
            variable=self.mode_var,
            values=["101", "301", "501", "701", "Custom"],
            command=self._on_mode_changed,
            width=180,
        )
        self.mode_menu.grid(row=6, column=0, sticky="w", padx=16, pady=(4, 12))

        self.custom_score_entry = ctk.CTkEntry(self.setup_frame, textvariable=self.custom_score_var, width=120)
        self.custom_score_entry.grid(row=6, column=1, sticky="w", padx=16, pady=(4, 12))
        self.custom_score_entry.grid_remove()

        ctk.CTkLabel(self.setup_frame, text="Match format").grid(row=7, column=0, sticky="w", padx=16)
        self.preset_menu = ctk.CTkOptionMenu(
            self.setup_frame,
            variable=self.preset_var,
            values=[
                "Single leg",
                "Best of 5 legs",
                "Best of 3 sets, best of 5 legs",
                "Best of 5 sets, best of 5 legs",
                "Custom",
            ],
            command=self._on_preset_changed,
            width=320,
        )
        self.preset_menu.grid(row=8, column=0, sticky="w", padx=16, pady=(4, 12))

        self.custom_match_frame = ctk.CTkFrame(self.setup_frame)
        self.custom_match_frame.grid(row=9, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        self.custom_match_frame.grid_columnconfigure(0, weight=1)
        self.custom_match_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.custom_match_frame, text="Legs to win set").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        ctk.CTkLabel(self.custom_match_frame, text="Sets to win match").grid(row=0, column=1, sticky="w", padx=10, pady=(10, 4))
        self.custom_legs_entry = ctk.CTkEntry(self.custom_match_frame, textvariable=self.custom_legs_var, width=120)
        self.custom_legs_entry.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        self.custom_sets_entry = ctk.CTkEntry(self.custom_match_frame, textvariable=self.custom_sets_var, width=120)
        self.custom_sets_entry.grid(row=1, column=1, sticky="w", padx=10, pady=(0, 10))
        self.custom_match_frame.grid_remove()

        ctk.CTkButton(self.setup_frame, text="Start Match", command=self.start_match, width=140).grid(
            row=10, column=0, sticky="w", padx=16, pady=(8, 16)
        )

        history_frame = ctk.CTkFrame(self.setup_frame)
        history_frame.grid(row=11, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 16))
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(history_frame, text="Match history").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        search_row = ctk.CTkFrame(history_frame, fg_color="transparent")
        search_row.grid(row=0, column=1, sticky="e", padx=10, pady=(10, 4))
        ctk.CTkLabel(search_row, text="Search player").grid(row=0, column=0, padx=(0, 6))
        self.history_search_entry = ctk.CTkEntry(search_row, textvariable=self.history_search_var, width=180)
        self.history_search_entry.grid(row=0, column=1, padx=(0, 6))
        self.history_search_entry.bind("<Return>", lambda _event: self.refresh_history_options())
        ctk.CTkButton(search_row, text="Apply", command=self.refresh_history_options, width=80).grid(row=0, column=2, padx=(0, 6))
        ctk.CTkButton(search_row, text="Clear", command=self._clear_history_search, width=80).grid(row=0, column=3)

        self.history_menu = ctk.CTkOptionMenu(
            history_frame,
            variable=self.history_selection_var,
            values=["No saved matches"],
            width=420,
        )
        self.history_menu.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        actions = ctk.CTkFrame(history_frame, fg_color="transparent")
        actions.grid(row=1, column=1, sticky="e", padx=10, pady=(0, 10))
        ctk.CTkButton(actions, text="Refresh", command=self.refresh_history_options, width=100).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(actions, text="View selected", command=self._show_selected_history, width=120).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(actions, text="Export JSON", command=self._export_selected_history_json, width=110).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(actions, text="Export CSV", command=self._export_selected_history_csv, width=100).grid(row=0, column=3, padx=(0, 8))
        ctk.CTkButton(actions, text="Delete", command=self._delete_selected_history, width=90).grid(row=0, column=4)

    def _build_game_ui(self) -> None:
        self.game_frame.grid_columnconfigure(0, weight=2)
        self.game_frame.grid_columnconfigure(1, weight=2)
        self.game_frame.grid_columnconfigure(2, weight=1)
        self.game_frame.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(self.game_frame, text="Live Match", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 8)
        )
        ctk.CTkLabel(self.game_frame, textvariable=self.round_label_var).grid(row=1, column=0, sticky="w", padx=16)
        ctk.CTkLabel(self.game_frame, textvariable=self.current_label_var).grid(row=1, column=1, sticky="w", padx=16)

        self.checkout_banner = ctk.CTkFrame(self.game_frame, fg_color=("#fde68a", "#78350f"), border_width=1, border_color="#f59e0b")
        self.checkout_banner.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(8, 12))
        self.checkout_banner.grid_columnconfigure(0, weight=1)
        self.checkout_title_label = ctk.CTkLabel(
            self.checkout_banner,
            text="CHECKOUT AVAILABLE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#7c2d12", "#fef3c7"),
        )
        self.checkout_title_label.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        self.checkout_value_label = ctk.CTkLabel(
            self.checkout_banner,
            textvariable=self.checkout_label_var,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#431407", "#fef9c3"),
            anchor="w",
            justify="left",
        )
        self.checkout_value_label.grid(row=1, column=0, sticky="w", padx=12, pady=(2, 10))
        self.checkout_banner.grid_remove()

        self.scoreboard_frame = ctk.CTkFrame(self.game_frame)
        self.scoreboard_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=16)
        self.scoreboard_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.scoreboard_frame, fg_color=("gray82", "gray25"))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=5)
        header.grid_columnconfigure(1, weight=2)
        header.grid_columnconfigure(2, weight=2)
        header.grid_columnconfigure(3, weight=2)
        ctk.CTkLabel(header, text="Player", anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkLabel(header, text="Remaining", anchor="center", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, sticky="ew", padx=6)
        ctk.CTkLabel(header, text="Legs", anchor="center", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, sticky="ew", padx=6)
        ctk.CTkLabel(header, text="Sets", anchor="center", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, sticky="ew", padx=6)

        self.score_rows_container = ctk.CTkFrame(self.scoreboard_frame, fg_color="transparent")
        self.score_rows_container.grid(row=1, column=0, sticky="ew")
        self.score_rows_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.game_frame, text="3-dart score").grid(row=4, column=0, sticky="w", padx=16, pady=(12, 4))

        self.input_mode_switch = ctk.CTkSegmentedButton(
            self.game_frame,
            values=["Total", "Per dart"],
            variable=self.input_mode_var,
            command=self._on_input_mode_changed,
            width=220,
        )
        self.input_mode_switch.grid(row=4, column=1, sticky="w", padx=16, pady=(12, 4))

        self.total_input_frame = ctk.CTkFrame(self.game_frame, fg_color="transparent")
        self.total_input_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=16)
        self.score_entry = ctk.CTkEntry(self.total_input_frame, width=120)
        self.score_entry.grid(row=0, column=0, sticky="w")
        self.score_entry.bind("<Return>", lambda _event: self.submit_turn())

        self.submit_button = ctk.CTkButton(self.total_input_frame, text="Submit Turn", command=self.submit_turn, width=140)
        self.submit_button.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.per_dart_frame = ctk.CTkFrame(self.game_frame)
        self.per_dart_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16)
        self.per_dart_frame.grid_columnconfigure(0, weight=1)
        self.per_dart_frame.grid_columnconfigure(1, weight=1)
        self.per_dart_frame.grid_columnconfigure(2, weight=1)

        for idx, score_var in enumerate(self.dart_score_vars):
            ctk.CTkLabel(self.per_dart_frame, text=f"Dart {idx + 1}").grid(row=0, column=idx, sticky="w", padx=8, pady=(8, 2))
            entry = ctk.CTkEntry(self.per_dart_frame, textvariable=score_var, width=110)
            entry.grid(row=1, column=idx, sticky="w", padx=8, pady=(0, 8))
            entry.bind("<FocusIn>", lambda _event, i=idx: self._select_dart(i))
            entry.bind("<KeyRelease>", lambda _event, i=idx: self._on_per_dart_entry_changed(i))
            self.dart_entries.append(entry)

        self.per_dart_total_label = ctk.CTkLabel(
            self.per_dart_frame,
            textvariable=self.per_dart_total_var,
            font=ctk.CTkFont(weight="bold"),
        )
        self.per_dart_total_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))

        self.per_dart_submit_button = ctk.CTkButton(self.per_dart_frame, text="Submit Turn", command=self.submit_turn, width=140)
        self.per_dart_submit_button.grid(row=2, column=2, sticky="e", padx=8, pady=(0, 8))

        self.numpad_frame = ctk.CTkFrame(self.per_dart_frame)
        self.numpad_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for col in range(4):
            self.numpad_frame.grid_columnconfigure(col, weight=1)

        numeric_layout = [
            ("1", 0, 0),
            ("2", 0, 1),
            ("3", 0, 2),
            ("4", 1, 0),
            ("5", 1, 1),
            ("6", 1, 2),
            ("7", 2, 0),
            ("8", 2, 1),
            ("9", 2, 2),
            ("25", 3, 0),
            ("0", 3, 1),
            ("50", 3, 2),
        ]
        for label, row, col in numeric_layout:
            if label in {"25", "50"}:
                value = 25 if label == "25" else 50
                cmd = lambda val=value: self._set_current_dart_value(val)
            else:
                cmd = lambda val=label: self._append_numpad_digit(val)
            btn = ctk.CTkButton(self.numpad_frame, text=label, command=cmd, width=96)
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self.numpad_buttons.append(btn)

        controls_frame = ctk.CTkFrame(self.numpad_frame)
        controls_frame.grid(row=0, column=3, rowspan=4, sticky="nsew", padx=(8, 0), pady=4)
        controls_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(controls_frame, text="Multiplier").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.multiplier_switch = ctk.CTkSegmentedButton(
            controls_frame,
            values=["x1", "x2", "x3"],
            variable=self.dart_multiplier_var,
            width=120,
        )
        self.multiplier_switch.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        control_specs = [
            ("Back", self._numpad_backspace),
            ("Clear", self._clear_current_dart),
            ("Undo last", self._undo_last_dart),
            ("Clear all", self._clear_all_darts),
        ]
        for idx, (label, command) in enumerate(control_specs, start=2):
            btn = ctk.CTkButton(controls_frame, text=label, command=command)
            btn.grid(row=idx, column=0, sticky="ew", padx=8, pady=4)
            self.numpad_buttons.append(btn)

        self.per_dart_frame.grid_remove()

        side_actions = ctk.CTkFrame(self.game_frame, fg_color="transparent")
        side_actions.grid(row=5, column=2, sticky="e", padx=16)
        ctk.CTkButton(side_actions, text="End Match", command=self._end_match_midway, width=140).grid(row=0, column=0, pady=(0, 6))
        ctk.CTkButton(side_actions, text="New Match", command=self.reset_to_setup, width=140).grid(row=1, column=0)

        self.checkout_frame = ctk.CTkFrame(self.game_frame)
        self.checkout_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=16, pady=(10, 0))
        self.checkout_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.checkout_frame, textvariable=self.checkout_prompt_var).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.checkout_menu = ctk.CTkOptionMenu(self.checkout_frame, variable=self.checkout_count_var, values=["1"], width=110)
        self.checkout_menu.grid(row=0, column=1, padx=(0, 8), pady=10)
        ctk.CTkButton(self.checkout_frame, text="Confirm", command=self._confirm_checkout_darts, width=110).grid(
            row=0, column=2, padx=(0, 8), pady=10
        )
        ctk.CTkButton(self.checkout_frame, text="Cancel", command=self._cancel_checkout_darts, width=110).grid(
            row=0, column=3, padx=(0, 10), pady=10
        )
        self.checkout_frame.grid_remove()

        self.log_text = ctk.CTkTextbox(self.game_frame)
        self.log_text.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=16, pady=(12, 16))
        self.log_text.configure(state="disabled")

    def _build_stats_ui(self) -> None:
        self.stats_frame.grid_columnconfigure(0, weight=1)
        self.stats_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self.stats_frame,
            textvariable=self.stats_title_var,
            font=ctk.CTkFont(size=30, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(
            self.stats_frame,
            textvariable=self.stats_subtitle_var,
            font=ctk.CTkFont(size=18),
            text_color=("#475569", "#cbd5e1"),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        self.stats_textbox = ctk.CTkTextbox(self.stats_frame, font=ctk.CTkFont(size=18), wrap="word")
        self.stats_textbox.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self.stats_textbox.configure(state="disabled")

        buttons = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="e", padx=18, pady=(0, 16))
        ctk.CTkButton(buttons, text="Back to setup", command=self.reset_to_setup, width=140).grid(row=0, column=0)

    def _on_mode_changed(self, _selection: str = "") -> None:
        if self.mode_var.get() == "Custom":
            self.custom_score_entry.grid()
            self.custom_score_entry.configure(state="normal")
        else:
            self.custom_score_entry.grid_remove()

    def _on_preset_changed(self, _selection: str = "") -> None:
        if self.preset_var.get() == "Custom":
            self.custom_match_frame.grid()
        else:
            self.custom_match_frame.grid_remove()

    def _on_input_mode_changed(self, _selection: str = "") -> None:
        if self.input_mode_var.get() == "Per dart":
            self.total_input_frame.grid_remove()
            self.per_dart_frame.grid()
            self._select_dart(0)
            self.dart_entries[0].focus_set()
        else:
            self.per_dart_frame.grid_remove()
            self.total_input_frame.grid()
            self.score_entry.focus_set()

    def _focus_score_input(self) -> None:
        if self.input_mode_var.get() == "Per dart":
            self.dart_entries[self.selected_dart_index].focus_set()
        else:
            self.score_entry.focus_set()

    def _set_turn_input_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.score_entry.configure(state=state)
        self.submit_button.configure(state=state)
        self.per_dart_submit_button.configure(state=state)
        for entry in self.dart_entries:
            entry.configure(state=state)
        for btn in self.numpad_buttons:
            btn.configure(state=state)
        self.multiplier_switch.configure(state=state)
        self.input_mode_switch.configure(state=state)

    def _select_dart(self, index: int) -> None:
        self.selected_dart_index = max(0, min(2, index))

    def _multiplier_factor(self) -> int:
        return {"x1": 1, "x2": 2, "x3": 3}.get(self.dart_multiplier_var.get(), 1)

    def _parse_dart_value(self, raw: str) -> int:
        if raw.strip() == "":
            return 0
        value = int(raw)
        if value < 0 or value > 60:
            raise ValueError("Each dart must be between 0 and 60.")
        return value

    def _current_dart_var(self) -> tk.StringVar:
        return self.dart_score_vars[self.selected_dart_index]

    def _update_per_dart_total(self) -> None:
        total = 0
        for var in self.dart_score_vars:
            raw = var.get().strip()
            if raw == "":
                continue
            try:
                total += self._parse_dart_value(raw)
            except Exception:
                pass
        self.per_dart_total_var.set(f"Per-dart total: {total}")

    def _on_per_dart_entry_changed(self, dart_index: int) -> None:
        self.dart_base_inputs[dart_index] = ""
        self._update_per_dart_total()

    def _append_numpad_digit(self, digit: str) -> None:
        multiplier = self._multiplier_factor()
        current_base = self.dart_base_inputs[self.selected_dart_index]
        candidate = f"{current_base}{digit}"
        try:
            base_value = int(candidate)
        except ValueError:
            return

        if base_value * multiplier > 60:
            return

        self.dart_base_inputs[self.selected_dart_index] = candidate
        self._current_dart_var().set(str(base_value * multiplier))
        self._update_per_dart_total()

    def _numpad_backspace(self) -> None:
        current_base = self.dart_base_inputs[self.selected_dart_index]
        if current_base:
            current_base = current_base[:-1]
            self.dart_base_inputs[self.selected_dart_index] = current_base
            if current_base:
                self._current_dart_var().set(str(int(current_base) * self._multiplier_factor()))
            else:
                self._current_dart_var().set("")
        else:
            current = self._current_dart_var().get()
            self._current_dart_var().set(current[:-1])
        self._update_per_dart_total()

    def _clear_current_dart(self) -> None:
        self.dart_base_inputs[self.selected_dart_index] = ""
        self._current_dart_var().set("")
        self._update_per_dart_total()

    def _set_current_dart_value(self, value: int) -> None:
        if value < 0 or value > 60:
            return
        self.dart_base_inputs[self.selected_dart_index] = ""
        self._current_dart_var().set(str(value))
        self._update_per_dart_total()
        if self.selected_dart_index < 2:
            self._select_dart(self.selected_dart_index + 1)
            self.dart_entries[self.selected_dart_index].focus_set()

    def _undo_last_dart(self) -> None:
        for idx in range(2, -1, -1):
            if self.dart_score_vars[idx].get().strip() != "":
                self.dart_base_inputs[idx] = ""
                self.dart_score_vars[idx].set("")
                self._select_dart(idx)
                self.dart_entries[idx].focus_set()
                self._update_per_dart_total()
                return

    def _clear_all_darts(self) -> None:
        for var in self.dart_score_vars:
            var.set("")
        self.dart_base_inputs = ["", "", ""]
        self._select_dart(0)
        self.dart_entries[0].focus_set()
        self._update_per_dart_total()

    def _resolve_turn_score(self) -> int | None:
        if self.input_mode_var.get() == "Per dart":
            raw_values = [var.get().strip() for var in self.dart_score_vars]
            if all(value == "" for value in raw_values):
                messagebox.showerror("Invalid score", "Enter at least one dart score.")
                return None
            try:
                score = sum(self._parse_dart_value(value) for value in raw_values)
            except ValueError as error:
                messagebox.showerror("Invalid score", str(error))
                return None
            if score > 180:
                messagebox.showerror("Invalid score", "3-dart total cannot be above 180.")
                return None
            return score

        raw_score = self.score_entry.get().strip()
        try:
            score = int(raw_score)
        except ValueError:
            messagebox.showerror("Invalid score", "Enter a number between 0 and 180.")
            return None
        if score < 0 or score > 180:
            messagebox.showerror("Invalid score", "Enter a number between 0 and 180.")
            return None
        return score

    def _on_more_players_toggled(self) -> None:
        if self.more_players_var.get():
            self.more_players_frame.grid()
            if not self.extra_player_entries:
                self._add_extra_player_field()
        else:
            self.more_players_frame.grid_remove()

    def _add_extra_player_field(self) -> None:
        index = len(self.extra_player_entries) + 3
        var = tk.StringVar(value=f"Player {index}")
        entry = ctk.CTkEntry(self.more_players_entries_frame, textvariable=var, width=240)
        entry.grid(row=len(self.extra_player_entries), column=0, sticky="w", padx=8, pady=(8, 0))
        self.extra_player_vars.append(var)
        self.extra_player_entries.append(entry)

    def _remove_extra_player_field(self) -> None:
        if not self.extra_player_entries:
            return
        entry = self.extra_player_entries.pop()
        entry.destroy()
        self.extra_player_vars.pop()

    def _parse_players(self) -> list[str]:
        first = self.player1_var.get().strip()
        second = self.player2_var.get().strip()
        if not first or not second:
            raise ValueError("Enter names for Player 1 and Player 2.")

        names = [first, second]
        if self.more_players_var.get():
            extras = [var.get().strip() for var in self.extra_player_vars if var.get().strip()]
            if not extras:
                raise ValueError("Add at least one more player or disable the extra players option.")
            names.extend(extras)
        return names

    def _resolve_start_score(self) -> int:
        mode = self.mode_var.get()
        if mode == "Custom":
            return self._parse_positive_int(self.custom_score_var.get(), "custom start score")
        return int(mode)

    def _resolve_format(self) -> tuple[int, int]:
        preset = self.preset_var.get()
        presets = {
            "Single leg": (1, 1),
            "Best of 5 legs": (3, 1),
            "Best of 3 sets, best of 5 legs": (3, 2),
            "Best of 5 sets, best of 5 legs": (3, 3),
        }
        if preset in presets:
            return presets[preset]
        legs = self._parse_positive_int(self.custom_legs_var.get(), "legs to win a set")
        sets_ = self._parse_positive_int(self.custom_sets_var.get(), "sets to win match")
        return legs, sets_

    def _parse_positive_int(self, raw: str, label: str) -> int:
        try:
            value = int(raw)
        except ValueError as error:
            raise ValueError(f"Enter a valid number for {label}.") from error
        if value < 1:
            raise ValueError(f"{label.capitalize()} must be at least 1.")
        return value

    def _history_option_label(self, match_row: dict[str, object]) -> str:
        winner = str(match_row.get("winner_name") or "-")
        played_at = str(match_row.get("played_at") or "")
        ended_early = bool(match_row.get("ended_early"))
        status = "Ended early" if ended_early else f"Winner: {winner}"
        return f"#{match_row['id']} | {played_at} | {status}"

    def refresh_history_options(self) -> None:
        entries = list_matches(limit=200, player_name_query=self.history_search_var.get())
        self.history_option_to_id = {}

        if not entries:
            fallback = "No saved matches"
            self.history_menu.configure(values=[fallback])
            self.history_selection_var.set(fallback)
            return

        labels: list[str] = []
        for row in entries:
            label = self._history_option_label(row)
            labels.append(label)
            self.history_option_to_id[label] = int(row["id"])

        self.history_menu.configure(values=labels)
        self.history_selection_var.set(labels[0])

    def _clear_history_search(self) -> None:
        self.history_search_var.set("")
        self.refresh_history_options()

    def _selected_history_match_id(self) -> int | None:
        option = self.history_selection_var.get()
        return self.history_option_to_id.get(option)

    def _show_selected_history(self) -> None:
        match_id = self._selected_history_match_id()
        if match_id is None:
            messagebox.showinfo("Match history", "No saved match selected.")
            return

        match_data = get_match(match_id)
        if match_data is None:
            messagebox.showerror("Match history", "Could not load selected match.")
            self.refresh_history_options()
            return

        ended_early = bool(match_data.get("ended_early"))
        winner_name = str(match_data.get("winner_name") or "-")
        played_at = str(match_data.get("played_at") or "")
        title = f"Saved match #{match_id}"
        subtitle = (
            f"{played_at} | Ended early"
            if ended_early
            else f"{played_at} | Winner: {winner_name}"
        )

        player_records = match_data.get("players", [])
        stats_text = self._format_stats_text(player_records)
        self._show_stats_screen(title, subtitle, stats_text)

    def _delete_selected_history(self) -> None:
        match_id = self._selected_history_match_id()
        if match_id is None:
            messagebox.showinfo("Match history", "No saved match selected.")
            return

        confirmed = messagebox.askyesno("Delete match", f"Delete saved match #{match_id}? This cannot be undone.")
        if not confirmed:
            return

        deleted = delete_match(match_id)
        if not deleted:
            messagebox.showerror("Match history", "Could not delete selected match.")
            return

        self.refresh_history_options()
        messagebox.showinfo("Match history", f"Deleted match #{match_id}.")

    def _export_selected_history_json(self) -> None:
        match_id = self._selected_history_match_id()
        if match_id is None:
            messagebox.showinfo("Match history", "No saved match selected.")
            return

        match_data = get_match(match_id)
        if match_data is None:
            messagebox.showerror("Match history", "Could not load selected match.")
            self.refresh_history_options()
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export match as JSON",
            defaultextension=".json",
            initialfile=f"match_{match_id}.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8") as file_handle:
            json.dump(match_data, file_handle, indent=2)

        messagebox.showinfo("Match history", f"Exported JSON to:\n{file_path}")

    def _export_selected_history_csv(self) -> None:
        match_id = self._selected_history_match_id()
        if match_id is None:
            messagebox.showinfo("Match history", "No saved match selected.")
            return

        match_data = get_match(match_id)
        if match_data is None:
            messagebox.showerror("Match history", "Could not load selected match.")
            self.refresh_history_options()
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export match as CSV",
            defaultextension=".csv",
            initialfile=f"match_{match_id}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8", newline="") as file_handle:
            writer = csv.writer(file_handle)
            writer.writerow([
                "match_id",
                "played_at",
                "winner_name",
                "ended_early",
                "start_score",
                "legs_to_win_set",
                "sets_to_win_match",
                "player_name",
                "sets_won",
                "legs_won",
                "turns_played",
                "darts_thrown",
                "total_scored",
                "highest_score",
                "highest_checkout",
            ])

            for record in match_data.get("players", []):
                writer.writerow([
                    match_data.get("id"),
                    match_data.get("played_at"),
                    match_data.get("winner_name") or "",
                    1 if bool(match_data.get("ended_early")) else 0,
                    match_data.get("start_score"),
                    match_data.get("legs_to_win_set"),
                    match_data.get("sets_to_win_match"),
                    record.get("name"),
                    record.get("sets_won"),
                    record.get("legs_won"),
                    record.get("turns_played"),
                    record.get("darts_thrown"),
                    record.get("total_scored"),
                    record.get("highest_score"),
                    record.get("highest_checkout"),
                ])

        messagebox.showinfo("Match history", f"Exported CSV to:\n{file_path}")

    def _current_player(self) -> PlayerState:
        return self.players[(self.leg_start_player_index + self.turn_offset) % len(self.players)]

    def _set_textbox(self, widget: ctk.CTkTextbox, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        cleaned = value.lstrip("#")
        return int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16)

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in rgb)

    def _blend_color(self, start_hex: str, end_hex: str, t: float) -> str:
        start = self._hex_to_rgb(start_hex)
        end = self._hex_to_rgb(end_hex)
        blended = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
        return self._rgb_to_hex(blended)

    def _apply_row_style(self, index: int, *, active: bool, light_color: str | None = None, dark_color: str | None = None) -> None:
        if index < 0 or index >= len(self.score_row_frames):
            return

        light = light_color or (self.row_active_light if active else self.row_normal_light)
        dark = dark_color or (self.row_active_dark if active else self.row_normal_dark)
        row = self.score_row_frames[index]
        row.configure(fg_color=(light, dark))

        # Keep text/font updates out of per-frame animation for smoothness.
        if light_color is None and dark_color is None:
            name_label = self.score_row_name_labels[index]
            player_name = self.players[index].name
            name_label.configure(
                text=f"> {player_name}" if active else player_name,
                font=ctk.CTkFont(weight="bold" if active else "normal"),
            )

    def _animate_turn_transition(self, from_index: int, to_index: int) -> None:
        if from_index == to_index:
            return
        if from_index < 0 or to_index < 0:
            return
        if from_index >= len(self.score_row_frames) or to_index >= len(self.score_row_frames):
            return

        if self.turn_animation_after_id is not None:
            self.after_cancel(self.turn_animation_after_id)
            self.turn_animation_after_id = None

        steps = 40
        interval_ms = 28

        def tick(step: int) -> None:
            t_linear = step / steps
            t = t_linear * t_linear * (3 - (2 * t_linear))
            from_light = self._blend_color(self.row_active_light, self.row_normal_light, t)
            from_dark = self._blend_color(self.row_active_dark, self.row_normal_dark, t)
            to_light = self._blend_color(self.row_normal_light, self.row_active_light, t)
            to_dark = self._blend_color(self.row_normal_dark, self.row_active_dark, t)

            self._apply_row_style(from_index, active=False, light_color=from_light, dark_color=from_dark)
            self._apply_row_style(to_index, active=True, light_color=to_light, dark_color=to_dark)

            if step < steps:
                self.turn_animation_after_id = self.after(interval_ms, lambda: tick(step + 1))
            else:
                self.turn_animation_after_id = None
                self._apply_row_style(from_index, active=False)
                self._apply_row_style(to_index, active=True)

        tick(0)

    def _ensure_scoreboard_rows(self) -> None:
        # Remove extra rows if player count shrank.
        while len(self.score_row_frames) > len(self.players):
            frame = self.score_row_frames.pop()
            frame.destroy()
            self.score_row_name_labels.pop()
            self.score_row_value_labels.pop()

        # Create missing rows if player count grew.
        while len(self.score_row_frames) < len(self.players):
            idx = len(self.score_row_frames)
            row = ctk.CTkFrame(self.score_rows_container, fg_color=(self.row_normal_light, self.row_normal_dark))
            row.grid(row=idx, column=0, sticky="ew", pady=(0, 6))
            row.grid_columnconfigure(0, weight=5)
            row.grid_columnconfigure(1, weight=2)
            row.grid_columnconfigure(2, weight=2)
            row.grid_columnconfigure(3, weight=2)

            name_label = ctk.CTkLabel(row, text="", anchor="w")
            name_label.grid(row=0, column=0, sticky="w", padx=12, pady=8)
            remaining_label = ctk.CTkLabel(row, text="", anchor="center")
            remaining_label.grid(row=0, column=1, sticky="ew", padx=6)
            legs_label = ctk.CTkLabel(row, text="", anchor="center")
            legs_label.grid(row=0, column=2, sticky="ew", padx=6)
            sets_label = ctk.CTkLabel(row, text="", anchor="center")
            sets_label.grid(row=0, column=3, sticky="ew", padx=6)

            self.score_row_frames.append(row)
            self.score_row_name_labels.append(name_label)
            self.score_row_value_labels.append((remaining_label, legs_label, sets_label))

    def _render_scoreboard(self, active_index: int, transition_from_index: int | None = None) -> None:
        if self.turn_animation_after_id is not None:
            self.after_cancel(self.turn_animation_after_id)
            self.turn_animation_after_id = None

        self._ensure_scoreboard_rows()

        for idx, state in enumerate(self.players):
            is_current = idx == active_index
            name_label = self.score_row_name_labels[idx]
            remaining_label, legs_label, sets_label = self.score_row_value_labels[idx]

            name_label.configure(
                text=f"> {state.name}" if is_current else state.name,
                font=ctk.CTkFont(weight="bold" if is_current else "normal"),
            )
            remaining_label.configure(text=str(state.score))
            legs_label.configure(text=f"{state.legs_in_set}/{self.legs_to_win_set}")
            sets_label.configure(text=f"{state.sets_won}/{self.sets_to_win_match}")
            self._apply_row_style(idx, active=is_current)

        if transition_from_index is not None and transition_from_index != active_index:
            self._animate_turn_transition(transition_from_index, active_index)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_match(self) -> None:
        try:
            names = self._parse_players()
            self.start_score = self._resolve_start_score()
            self.legs_to_win_set, self.sets_to_win_match = self._resolve_format()
        except ValueError as error:
            messagebox.showerror("Invalid setup", str(error))
            return

        self.players = [PlayerState(name=name, score=self.start_score) for name in names]
        self.set_number = 1
        self.leg_number = 1
        self.leg_start_player_index = 0
        self.turn_offset = 0
        self._hide_checkout_prompt()

        self.setup_frame.pack_forget()
        self.game_frame.pack(fill="both", expand=True, padx=16, pady=16)

        self._set_textbox(self.log_text, "")
        self._append_log("Match started.")
        self.refresh_game_view()
        self._focus_score_input()

    def refresh_game_view(self, transition_from_index: int | None = None) -> None:
        if not self.players:
            return

        player = self._current_player()
        current_index = (self.leg_start_player_index + self.turn_offset) % len(self.players)
        self.round_label_var.set(f"Set {self.set_number}, Leg {self.leg_number}")
        self.current_label_var.set(f"Current player: {player.name}")

        hints = checkout_suggestions(player.score)
        if hints:
            self.checkout_label_var.set(hints[0])
            self.checkout_banner.grid()
            self.checkout_banner.configure(fg_color=("#fde68a", "#78350f"), border_color="#f59e0b")
            self.checkout_title_label.configure(text="CHECKOUT AVAILABLE")
            self.checkout_title_label.configure(text_color=("#7c2d12", "#fef3c7"))
            self.checkout_value_label.configure(text_color=("#431407", "#fef9c3"))
        else:
            self.checkout_banner.grid_remove()
        self._render_scoreboard(current_index, transition_from_index)

    def _show_checkout_prompt(self, player_name: str, valid_counts: list[int]) -> None:
        self.pending_valid_counts = valid_counts
        values = [str(count) for count in valid_counts]
        self.checkout_menu.configure(values=values)
        self.checkout_count_var.set(values[0])
        self.checkout_prompt_var.set(f"{player_name} checkout: how many darts used?")
        self.checkout_frame.grid()
        self._set_turn_input_enabled(False)
        self.checkout_menu.focus_set()

    def _hide_checkout_prompt(self) -> None:
        self.pending_checkout_player_index = None
        self.pending_checkout_score = 0
        self.pending_valid_counts = []
        self.checkout_count_var.set("")
        self.checkout_prompt_var.set("")
        self.checkout_frame.grid_remove()
        self._set_turn_input_enabled(True)

    def _confirm_checkout_darts(self) -> None:
        if self.pending_checkout_player_index is None:
            return

        try:
            darts_used = int(self.checkout_count_var.get())
        except ValueError:
            self._append_log("Checkout confirmation failed: select a dart count.")
            return

        if darts_used not in self.pending_valid_counts:
            self._append_log("Checkout confirmation failed: invalid dart count selected.")
            return

        player = self.players[self.pending_checkout_player_index]
        score = self.pending_checkout_score
        checkout_total = player.score

        player.highest_checkout = max(player.highest_checkout, checkout_total)
        player.score = 0
        player.total_scored += score
        player.highest_score = max(player.highest_score, score)
        player.darts_thrown += darts_used
        self._append_log(f"{player.name}: scored {score}, remaining 0.")

        self._hide_checkout_prompt()
        self.score_entry.delete(0, "end")
        self._handle_leg_winner(player)

    def _cancel_checkout_darts(self) -> None:
        if self.pending_checkout_player_index is None:
            return
        player = self.players[self.pending_checkout_player_index]
        player.turns_played -= 1
        self._append_log(f"{player.name}: checkout confirmation cancelled.")
        self._hide_checkout_prompt()
        self._focus_score_input()

    def submit_turn(self) -> None:
        if not self.players:
            return
        if self.pending_checkout_player_index is not None:
            self._append_log("Confirm checkout darts first.")
            return

        score = self._resolve_turn_score()
        if score is None:
            return

        player = self._current_player()
        player.turns_played += 1
        darts_used_this_turn = 3

        if score > player.score:
            player.darts_thrown += darts_used_this_turn
            self._append_log(f"{player.name}: bust ({score} is above remaining {player.score}).")
            self._advance_turn()
            return

        remaining = player.score - score
        if remaining == 1:
            player.darts_thrown += darts_used_this_turn
            self._append_log(f"{player.name}: bust (cannot leave 1).")
            self._advance_turn()
            return

        if remaining == 0:
            checkout_total = player.score
            valid_counts = possible_checkout_dart_counts(checkout_total)
            if not valid_counts:
                player.darts_thrown += darts_used_this_turn
                self._append_log(f"{player.name}: bust ({checkout_total} has no legal checkout).")
                self._advance_turn()
                return

            current_index = (self.leg_start_player_index + self.turn_offset) % len(self.players)
            self.pending_checkout_player_index = current_index
            self.pending_checkout_score = score
            self._show_checkout_prompt(player.name, valid_counts)
            return

        player.score = remaining
        player.total_scored += score
        player.highest_score = max(player.highest_score, score)
        player.darts_thrown += darts_used_this_turn
        self._append_log(f"{player.name}: scored {score}, remaining {player.score}.")

        self._advance_turn()

    def _advance_turn(self) -> None:
        previous_index = (self.leg_start_player_index + self.turn_offset) % len(self.players)
        self.turn_offset += 1
        self.score_entry.delete(0, "end")
        self._clear_all_darts()
        self.refresh_game_view(transition_from_index=previous_index)
        self._focus_score_input()

    def _reset_leg_scores(self) -> None:
        for player in self.players:
            player.score = self.start_score

    def _reset_set_legs(self) -> None:
        for player in self.players:
            player.legs_in_set = 0

    def _current_players_as_records(self) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for player in self.players:
            records.append(
                {
                    "name": player.name,
                    "sets_won": player.sets_won,
                    "legs_won": player.legs_won,
                    "turns_played": player.turns_played,
                    "darts_thrown": player.darts_thrown,
                    "total_scored": player.total_scored,
                    "highest_score": player.highest_score,
                    "highest_checkout": player.highest_checkout,
                }
            )
        return records

    def _format_stats_text(self, player_records: list[dict[str, object]]) -> str:
        lines: list[str] = ["Match statistics"]
        for record in player_records:
            turns_played = int(record.get("turns_played", 0))
            darts_thrown = int(record.get("darts_thrown", 0))
            total_scored = int(record.get("total_scored", 0))
            average_score = total_scored / turns_played if turns_played else 0.0
            three_dart_average = (total_scored * 3) / darts_thrown if darts_thrown else 0.0
            highest_checkout = int(record.get("highest_checkout", 0))
            highest_checkout_text = str(highest_checkout) if highest_checkout else "-"

            lines.extend(
                [
                    "",
                    str(record.get("name", "Player")),
                    f"  Sets won: {int(record.get('sets_won', 0))}",
                    f"  Legs won: {int(record.get('legs_won', 0))}",
                    f"  Average score (per turn): {average_score:.2f}",
                    f"  Three-dart average: {three_dart_average:.2f}",
                    f"  Highest score: {int(record.get('highest_score', 0))}",
                    f"  Highest checkout: {highest_checkout_text}",
                ]
            )
        return "\n".join(lines)

    def _save_match_history(self, *, winner_name: str | None, ended_early: bool) -> None:
        save_match(
            start_score=self.start_score,
            legs_to_win_set=self.legs_to_win_set,
            sets_to_win_match=self.sets_to_win_match,
            ended_early=ended_early,
            winner_name=winner_name,
            players=self._current_players_as_records(),
        )
        self.refresh_history_options()

    def _show_stats_screen(self, title: str, subtitle: str, stats_text: str) -> None:
        self.stats_title_var.set(title)
        self.stats_subtitle_var.set(subtitle)
        self._set_textbox(self.stats_textbox, stats_text)

        self.setup_frame.pack_forget()
        self.game_frame.pack_forget()
        self.stats_frame.pack(fill="both", expand=True, padx=16, pady=16)

    def _handle_leg_winner(self, player: PlayerState) -> None:
        player.legs_won += 1
        player.legs_in_set += 1
        self._append_log(f"{player.name} won leg {self.leg_number}.")

        if player.legs_in_set >= self.legs_to_win_set:
            player.sets_won += 1
            self._append_log(f"{player.name} won set {self.set_number}.")

            if player.sets_won >= self.sets_to_win_match:
                self.refresh_game_view()
                self._append_log(f"{player.name} won the match.")
                self._save_match_history(winner_name=player.name, ended_early=False)
                self._show_stats_screen(
                    f"{player.name} wins the match",
                    "Final player statistics",
                    self._format_stats_text(self._current_players_as_records()),
                )
                self.score_entry.delete(0, "end")
                return

            self._reset_set_legs()
            self.set_number += 1
            self.leg_number = 1
        else:
            self.leg_number += 1

        self.leg_start_player_index = (self.leg_start_player_index + 1) % len(self.players)
        self.turn_offset = 0
        self._reset_leg_scores()
        self.score_entry.delete(0, "end")
        self.refresh_game_view()
        self._focus_score_input()

    def _end_match_midway(self) -> None:
        if not self.players:
            return
        confirmed = messagebox.askyesno("End match", "End this match now and show current statistics?")
        if not confirmed:
            return
        self._append_log("Match ended manually.")
        self._save_match_history(winner_name=None, ended_early=True)
        self._show_stats_screen(
            "Match ended early",
            "Final player statistics",
            self._format_stats_text(self._current_players_as_records()),
        )

    def reset_to_setup(self) -> None:
        if self.turn_animation_after_id is not None:
            self.after_cancel(self.turn_animation_after_id)
            self.turn_animation_after_id = None
        self.players = []
        self._hide_checkout_prompt()
        self.game_frame.pack_forget()
        self.stats_frame.pack_forget()
        self.setup_frame.pack(fill="both", expand=True, padx=16, pady=16)
        self.refresh_history_options()


def main() -> None:
    app = DartsUI()
    app.mainloop()


if __name__ == "__main__":
    main()
