#!/usr/bin/env python3
"""Creates anime_catalog.db with sample data using only the standard library."""

import os
import sqlite3

DB_FILE = "anime_catalog.db"

STUDIOS = [
    # (studio_id, name, country, founded_year)
    (1, "Madhouse", "Japan", 1972),
    (2, "Kyoto Animation", "Japan", 1981),
    (3, "Bones", "Japan", 1998),
    (4, "MAPPA", "Japan", 2011),
    (5, "Sunrise", "Japan", 1972),
    (6, "Wit Studio", "Japan", 2012),
    (7, "A-1 Pictures", "Japan", 2005),
    (8, "Production I.G", "Japan", 1987),
]

ANIME = [
    # (anime_id, title, genre, release_year, episodes, rating, status, is_archived)
    (1, "Fullmetal Alchemist: Brotherhood", "Action", 2009, 64, 9.1, "Completed", 0),
    (2, "Attack on Titan", "Action", 2013, 87, 9.0, "Completed", 0),
    (3, "Jujutsu Kaisen", "Action", 2020, 47, 8.6, "Airing", 0),
    (4, "Cowboy Bebop", "Sci-Fi", 1998, 26, 8.8, "Completed", 0),
    (5, "Steins;Gate", "Sci-Fi", 2011, 24, 9.1, "Completed", 0),
    (6, "Psycho-Pass", "Sci-Fi", 2012, 22, 8.4, "Completed", 1),
    (7, "Planetes", "Sci-Fi", 2003, 26, 8.2, "Completed", 1),
    (8, "Death Note", "Mystery", 2006, 37, 8.6, "Completed", 0),
    (9, "Monster", "Mystery", 2004, 74, 8.9, "Completed", 0),
    (10, "Hyouka", "Mystery", 2012, 22, 8.0, "Completed", 0),
    (11, "Erased", "Mystery", 2016, 12, 8.3, "Completed", 1),
    (12, "K-On!", "Slice of Life", 2009, 14, 7.9, "Completed", 0),
    (13, "Barakamon", "Slice of Life", 2014, 12, 8.4, "Completed", 0),
    (14, "Non Non Biyori", "Slice of Life", 2013, 12, 8.3, "Completed", 0),
    (15, "Your Lie in April", "Drama", 2014, 22, 8.7, "Completed", 0),
    (16, "Violet Evergarden", "Drama", 2018, 13, 8.5, "Completed", 0),
    (17, "Clannad: After Story", "Drama", 2008, 24, 9.0, "Completed", 0),
    (18, "Vinland Saga", "Drama", 2019, 48, 8.8, "Airing", 0),
    (19, "Hunter x Hunter", "Action", 2011, 148, 9.0, "Completed", 0),
    (20, "Berserk (1997)", "Drama", 1997, 25, 8.5, "Hiatus", 1),
]

WATCH_LOGS = [
    # (log_id, anime_id, studio_id, episodes_watched, user_score, watch_status)
    (1, 1, 3, 64, 9.5, "Completed"),
    (2, 2, 4, 87, 9.0, "Completed"),
    (3, 3, 4, 20, 8.5, "Watching"),
    (4, 4, 5, 26, 9.0, "Completed"),
    (5, 5, 6, 24, 9.5, "Completed"),
    (6, 6, 8, 22, 8.0, "Completed"),
    (7, 7, 5, 10, 6.5, "Dropped"),
    (8, 8, 1, 37, 8.5, "Completed"),
    (9, 9, 1, 30, 9.0, "Dropped"),
    (10, 10, 2, 22, 8.0, "Completed"),
    (11, 11, 7, 12, 8.0, "Completed"),
    (12, 12, 2, 14, 7.5, "Completed"),
    (13, 13, 7, 6, 7.0, "Dropped"),
    (14, 14, 7, 0, None, "Plan to Watch"),
    (15, 15, 7, 22, 9.0, "Completed"),
    (16, 16, 2, 13, 8.5, "Completed"),
    (17, 17, 2, 24, 10.0, "Completed"),
    (18, 18, 4, 15, 8.8, "Watching"),
    (19, 19, 1, 50, 8.5, "Dropped"),
    (20, 20, 8, 0, None, "Plan to Watch"),
    (21, 3, 4, 47, 8.7, "Completed"),
    (22, 1, 3, 12, 8.0, "Dropped"),
]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE anime (
            anime_id     INTEGER PRIMARY KEY,
            title        TEXT NOT NULL,
            genre        TEXT NOT NULL,
            release_year INTEGER,
            episodes     INTEGER,
            rating       REAL,
            status       TEXT,
            is_archived  INTEGER DEFAULT 0
        );

        CREATE TABLE studios (
            studio_id    INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            country      TEXT,
            founded_year INTEGER
        );

        CREATE TABLE watch_logs (
            log_id           INTEGER PRIMARY KEY,
            anime_id         INTEGER NOT NULL,
            studio_id        INTEGER NOT NULL,
            episodes_watched INTEGER,
            user_score       REAL,
            watch_status     TEXT,
            FOREIGN KEY (anime_id)  REFERENCES anime(anime_id),
            FOREIGN KEY (studio_id) REFERENCES studios(studio_id)
        );
        """
    )


def populate(conn: sqlite3.Connection) -> None:
    conn.executemany("INSERT INTO studios VALUES (?, ?, ?, ?)", STUDIOS)
    conn.executemany("INSERT INTO anime VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ANIME)
    conn.executemany("INSERT INTO watch_logs VALUES (?, ?, ?, ?, ?, ?)", WATCH_LOGS)
    conn.commit()


def print_summary(conn: sqlite3.Connection) -> None:
    print(f"Database created: {DB_FILE}")
    print("-" * 32)
    for table in ("anime", "studios", "watch_logs"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<12} {count:>3} rows")
    archived = conn.execute(
        "SELECT COUNT(*) FROM anime WHERE is_archived = 1"
    ).fetchone()[0]
    dropped = conn.execute(
        "SELECT COUNT(*) FROM watch_logs WHERE watch_status = 'Dropped'"
    ).fetchone()[0]
    print("-" * 32)
    print(f"Archived anime:     {archived}")
    print(f"Dropped watch logs: {dropped}")


def main() -> None:
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        create_schema(conn)
        populate(conn)
        print_summary(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# Sample natural-language questions to query against this database:
#
# 1. "What are the top 5 highest-rated anime that are not archived?"
# 2. "How many completed watch logs does each studio have? (Count only
#     'Completed' logs, and exclude archived anime.)"
# 3. "What is the average user score per genre, using only completed watch
#     logs for non-archived anime?"
# 4. "Which anime did I drop, and how many episodes had I watched of each?"
# 5. "List each studio's name along with the total episodes I've watched
#     across all of its non-archived anime, sorted from most to least."
# ---------------------------------------------------------------------------