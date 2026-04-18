from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


THROW_POOL: List[Tuple[str, int, bool]] = []
CHECKOUT_CHART_FILE = Path(__file__).with_name("checkout.json")

# Commonly preferred finishing doubles (roughly by player comfort in many charts).
DOUBLE_FINISH_PRIORITY = [20, 16, 18, 12, 10, 8, 14, 6, 4, 2, 15, 13, 11, 9, 7, 5, 3, 1, 17, 19]


def build_throw_pool() -> List[Tuple[str, int, bool]]:
    pool: List[Tuple[str, int, bool]] = []
    for n in range(1, 21):
        pool.append((f"S{n}", n, False))
        pool.append((f"D{n}", 2 * n, True))
        pool.append((f"T{n}", 3 * n, False))
    pool.append(("SB", 25, False))
    pool.append(("DB", 50, True))
    return pool


THROW_POOL = build_throw_pool()


def throw_rank(label: str) -> Tuple[int, int]:
    if label == "DB":
        return (4, 50)
    if label == "SB":
        return (1, 25)
    prefix = label[0]
    value = int(label[1:])
    multiplier = {"T": 3, "D": 2, "S": 1}.get(prefix, 0)
    return (multiplier, value)


def format_route(route: Sequence[str]) -> str:
    return " | ".join(display_throw_label(label) for label in route)


def display_throw_label(label: str) -> str:
    if label == "DB":
        return "Bull"
    if label == "SB":
        return "Outer Bull"
    if label.startswith("T"):
        return f"Triple {int(label[1:])}"
    if label.startswith("D"):
        return f"Double {int(label[1:])}"
    if label.startswith("S"):
        return f"Single {int(label[1:])}"
    return label


def normalize_chart_token(token: str) -> str:
    cleaned = token.strip().upper()
    if cleaned == "BULL":
        return "DB"
    if cleaned.startswith(("S", "D", "T")):
        return cleaned
    return f"S{int(cleaned)}"


@lru_cache(maxsize=1)
def checkout_chart() -> Dict[int, Tuple[str, ...]]:
    with CHECKOUT_CHART_FILE.open("r", encoding="utf-8") as file_handle:
        raw: Dict[str, List[str]] = json.load(file_handle)

    result: Dict[int, Tuple[str, ...]] = {}
    for key, sequence in raw.items():
        score = int(key)
        result[score] = tuple(normalize_chart_token(token) for token in sequence)
    return result


def possible_checkout_dart_counts(score: int) -> List[int]:
    routes = checkout_routes().get(score, [])
    return sorted({len(route) for route in routes})


def finishing_dart_rank(label: str) -> int:
    if label == "DB":
        return 30
    if not label.startswith("D"):
        return 999
    number = int(label[1:])
    if number in DOUBLE_FINISH_PRIORITY:
        return DOUBLE_FINISH_PRIORITY.index(number)
    return 100 + number


def route_quality(route: Sequence[str]) -> Tuple[int, ...]:
    # Lower is better.
    # 1) Fewer darts.
    # 2) Avoid setup doubles before the finishing dart.
    # 3) Prefer classic finishing doubles.
    # 4) Prefer simpler/higher setup darts.
    # 5) Avoid awkward low doubles like D1 unless necessary.
    darts = len(route)
    finish = route[-1]
    finish_pref = finishing_dart_rank(finish)

    setup_double_count = 0
    setup_nontriple_penalty = 0
    setup_value_bias = 0
    for label in route[:-1]:
        if label == "SB":
            setup_nontriple_penalty += 1
            continue
        if label == "DB":
            setup_double_count += 1
            setup_nontriple_penalty += 2
            continue
        mult = label[0]
        value = int(label[1:])
        if mult == "S":
            setup_nontriple_penalty += 1
        elif mult == "D":
            setup_double_count += 1
            setup_nontriple_penalty += 2
        else:  # T
            setup_nontriple_penalty += 0
        setup_value_bias += (20 - value)

    finish_awkward_penalty = 6 if finish == "D1" else 0

    # Keep a deterministic tie-breaker.
    tie_break: List[int] = []
    for label in route:
        pref, value = throw_rank(label)
        tie_break.extend([-pref, -value])

    return (
        darts,
        setup_double_count,
        finish_pref,
        finish_awkward_penalty,
        setup_nontriple_penalty,
        setup_value_bias,
        *tie_break,
    )


@lru_cache(maxsize=1)
def checkout_routes() -> Dict[int, List[Tuple[str, ...]]]:
    routes: Dict[int, List[Tuple[str, ...]]] = {}
    for label1, score1, is_finish1 in THROW_POOL:
        if is_finish1:
            total = score1
            if 2 <= total <= 170:
                routes.setdefault(total, []).append((label1,))

        for label2, score2, is_finish2 in THROW_POOL:
            total = score1 + score2
            if is_finish2 and 2 <= total <= 170:
                routes.setdefault(total, []).append((label1, label2))

            for label3, score3, is_finish3 in THROW_POOL:
                total = score1 + score2 + score3
                if is_finish3 and 2 <= total <= 170:
                    routes.setdefault(total, []).append((label1, label2, label3))

    for total, options in routes.items():
        unique_options = list(dict.fromkeys(options))
        unique_options.sort(key=route_sort_key)
        routes[total] = unique_options
    return routes


def route_sort_key(route: Sequence[str]) -> Tuple[int, ...]:
    return route_quality(route)


def checkout_suggestions(remaining: int, limit: int = 3) -> List[str]:
    chart_route = checkout_chart().get(remaining)
    if chart_route:
        return [format_route(chart_route)]
    return []


def parse_player_names(raw: str) -> List[str]:
    names = [part.strip() for part in raw.split(",")]
    return [name for name in names if name]


def prompt_int(prompt: str, *, min_value: int | None = None, max_value: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Enter a number.")
            continue

        if min_value is not None and value < min_value:
            print(f"Enter a value of at least {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Enter a value of at most {max_value}.")
            continue
        return value


def prompt_checkout_darts_used(valid_counts: Sequence[int]) -> int:
    text_options = "/".join(str(count) for count in valid_counts)
    while True:
        raw = input(f"How many darts did you use to finish? ({text_options}): ").strip()
        try:
            used = int(raw)
        except ValueError:
            print("Enter a number.")
            continue
        if used not in valid_counts:
            print(f"That finish is not possible with {used} dart(s) for this checkout.")
            continue
        return used


@dataclass
class Player:
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


def choose_mode() -> int:
    modes = [101, 301, 501, 701]
    print("Select a game mode:")
    for idx, mode in enumerate(modes, start=1):
        print(f"  {idx}. {mode}")
    print("  5. Custom")

    choice = prompt_int("Choose a mode: ", min_value=1, max_value=5)
    if choice == 5:
        return prompt_int("Starting score: ", min_value=1)
    return modes[choice - 1]


def choose_match_format() -> Tuple[int, int]:
    print("\nMatch format")

    presets: List[Tuple[str, int, int]] = [
        ("Single leg", 1, 1),
        ("Best of 5 legs", 3, 1),
        ("Best of 3 sets, best of 5 legs", 3, 2),
        ("Best of 5 sets, best of 5 legs", 3, 3),
    ]

    print("Choose a preset:")
    for idx, (label, legs, sets_) in enumerate(presets, start=1):
        print(f"  {idx}. {label} (first to {legs} legs, first to {sets_} sets)")
    custom_index = len(presets) + 1
    print(f"  {custom_index}. Custom")

    choice = prompt_int("Match format: ", min_value=1, max_value=custom_index)
    if choice == custom_index:
        print("Enter how many legs are needed to win a set.")
        legs_to_win_set = prompt_int("Legs to win a set (for example 3): ", min_value=1)
        print("Enter how many sets are needed to win the match.")
        sets_to_win_match = prompt_int("Sets to win match (for example 3): ", min_value=1)
        return legs_to_win_set, sets_to_win_match

    _, legs_to_win_set, sets_to_win_match = presets[choice - 1]
    return legs_to_win_set, sets_to_win_match


def print_scoreboard(players: Sequence[Player]) -> None:
    print("\nScores:")
    for player in players:
        print(f"  {player.name}: {player.score}")


def print_match_score(players: Sequence[Player], legs_to_win_set: int, sets_to_win_match: int) -> None:
    print("\nMatch score:")
    for player in players:
        print(
            f"  {player.name}: "
            f"Sets {player.sets_won}/{sets_to_win_match}, "
            f"Legs {player.legs_in_set}/{legs_to_win_set}"
        )


def reset_leg_scores(players: Sequence[Player], start_score: int) -> None:
    for player in players:
        player.score = start_score


def reset_set_legs(players: Sequence[Player]) -> None:
    for player in players:
        player.legs_in_set = 0


def print_match_statistics(players: Sequence[Player]) -> None:
    print("\nMatch statistics:")
    for player in players:
        average_score = player.total_scored / player.turns_played if player.turns_played else 0.0
        three_dart_average = (player.total_scored * 3) / player.darts_thrown if player.darts_thrown else 0.0
        highest_checkout_text = str(player.highest_checkout) if player.highest_checkout else "-"

        print(f"\n  {player.name}")
        print(f"    Sets won: {player.sets_won}")
        print(f"    Legs won: {player.legs_won}")
        print(f"    Average score (per turn): {average_score:.2f}")
        print(f"    Three-dart average: {three_dart_average:.2f}")
        print(f"    Highest score: {player.highest_score}")
        print(f"    Highest checkout: {highest_checkout_text}")


def play_game() -> None:
    print("Darts counter")
    names = []
    while not names:
        names = parse_player_names(input("Enter player names, comma separated: "))
        if not names:
            print("Add at least one player.")

    start_score = choose_mode()
    legs_to_win_set, sets_to_win_match = choose_match_format()
    players = [Player(name=name, score=start_score) for name in names]

    set_number = 1
    leg_number = 1
    leg_start_player_index = 0

    print_match_score(players, legs_to_win_set, sets_to_win_match)
    print_scoreboard(players)
    while True:
        print(f"\n=== Set {set_number}, Leg {leg_number} ===")
        turn = 0
        while True:
            player = players[(leg_start_player_index + turn) % len(players)]
            print(f"\n{player.name}'s turn. Remaining: {player.score}")

            hints = checkout_suggestions(player.score)
            if hints:
                print("Checkout:")
                for suggestion in hints:
                    print(f"  {suggestion}")

            score = prompt_int("3-dart score: ", min_value=0, max_value=180)
            player.turns_played += 1
            darts_used_this_turn = 3

            if score > player.score:
                player.darts_thrown += darts_used_this_turn
                print("Bust: score is higher than the remaining total.")
                print_scoreboard(players)
                turn += 1
                continue

            remaining = player.score - score

            if remaining == 1:
                player.darts_thrown += darts_used_this_turn
                print("Bust: you cannot leave 1.")
                print_scoreboard(players)
                turn += 1
                continue

            if remaining == 0:
                checkout_total = player.score
                valid_counts = possible_checkout_dart_counts(checkout_total)
                if not valid_counts:
                    player.darts_thrown += darts_used_this_turn
                    print(f"Bust: {checkout_total} cannot be finished with a legal checkout.")
                    print_scoreboard(players)
                    turn += 1
                    continue

                darts_used = prompt_checkout_darts_used(valid_counts)
                darts_used_this_turn = darts_used
                player.highest_checkout = max(player.highest_checkout, checkout_total)

            player.score = remaining
            player.total_scored += score
            player.highest_score = max(player.highest_score, score)
            player.darts_thrown += darts_used_this_turn
            print_scoreboard(players)

            if player.score == 0:
                player.legs_won += 1
                player.legs_in_set += 1
                print(f"\n{player.name} wins leg {leg_number}.")
                print_match_score(players, legs_to_win_set, sets_to_win_match)

                if player.legs_in_set >= legs_to_win_set:
                    player.sets_won += 1
                    print(f"\n{player.name} wins set {set_number}.")

                    if player.sets_won >= sets_to_win_match:
                        print(f"\n{player.name} wins the match.")
                        print_match_statistics(players)
                        return

                    reset_set_legs(players)
                    set_number += 1
                    leg_number = 1
                else:
                    leg_number += 1

                leg_start_player_index = (leg_start_player_index + 1) % len(players)
                reset_leg_scores(players, start_score)
                print_scoreboard(players)
                break

            turn += 1


def main() -> None:
    play_game()


if __name__ == "__main__":
    main()
