from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path(__file__).with_name("match_history.sqlite3")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                played_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                start_score INTEGER NOT NULL,
                legs_to_win_set INTEGER NOT NULL,
                sets_to_win_match INTEGER NOT NULL,
                ended_early INTEGER NOT NULL,
                winner_name TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS match_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sets_won INTEGER NOT NULL,
                legs_won INTEGER NOT NULL,
                turns_played INTEGER NOT NULL,
                darts_thrown INTEGER NOT NULL,
                total_scored INTEGER NOT NULL,
                highest_score INTEGER NOT NULL,
                highest_checkout INTEGER NOT NULL,
                FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE
            )
            """
        )


def save_match(
    *,
    start_score: int,
    legs_to_win_set: int,
    sets_to_win_match: int,
    ended_early: bool,
    winner_name: Optional[str],
    players: List[Dict[str, Any]],
) -> int:
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO matches (
                start_score,
                legs_to_win_set,
                sets_to_win_match,
                ended_early,
                winner_name
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                start_score,
                legs_to_win_set,
                sets_to_win_match,
                1 if ended_early else 0,
                winner_name,
            ),
        )
        match_id = int(cursor.lastrowid)

        for player in players:
            connection.execute(
                """
                INSERT INTO match_players (
                    match_id,
                    name,
                    sets_won,
                    legs_won,
                    turns_played,
                    darts_thrown,
                    total_scored,
                    highest_score,
                    highest_checkout
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    player["name"],
                    player["sets_won"],
                    player["legs_won"],
                    player["turns_played"],
                    player["darts_thrown"],
                    player["total_scored"],
                    player["highest_score"],
                    player["highest_checkout"],
                ),
            )
        return match_id


def list_matches(limit: int = 100, player_name_query: str = "") -> List[Dict[str, Any]]:
    normalized_query = player_name_query.strip().lower()

    with _connect() as connection:
        if normalized_query:
            rows = connection.execute(
                """
                SELECT DISTINCT m.id, m.played_at, m.winner_name, m.ended_early,
                       m.start_score, m.legs_to_win_set, m.sets_to_win_match
                FROM matches m
                JOIN match_players p ON p.match_id = m.id
                WHERE lower(p.name) LIKE ?
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (f"%{normalized_query}%", limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, played_at, winner_name, ended_early, start_score,
                       legs_to_win_set, sets_to_win_match
                FROM matches
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def get_match(match_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as connection:
        match_row = connection.execute(
            """
            SELECT id, played_at, winner_name, ended_early, start_score,
                   legs_to_win_set, sets_to_win_match
            FROM matches
            WHERE id = ?
            """,
            (match_id,),
        ).fetchone()
        if match_row is None:
            return None

        player_rows = connection.execute(
            """
            SELECT name, sets_won, legs_won, turns_played, darts_thrown,
                   total_scored, highest_score, highest_checkout
            FROM match_players
            WHERE match_id = ?
            ORDER BY id ASC
            """,
            (match_id,),
        ).fetchall()

    result = dict(match_row)
    result["players"] = [dict(row) for row in player_rows]
    return result


def delete_match(match_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        return cursor.rowcount > 0
