import argparse
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "data" / "proxima.sqlite3"
SQLITE_SCHEMA_PATH = BASE_DIR.parent / "db" / "sqlite_schema.sql"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize or migrate SQLite schema.")
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_DATABASE_PATH", str(DEFAULT_SQLITE_PATH)),
        help="Path to SQLite database file.",
    )
    parser.add_argument(
        "--schema-path",
        default=str(SQLITE_SCHEMA_PATH),
        help="Path to SQLite schema SQL file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    schema_path = Path(args.schema_path).expanduser().resolve()

    if not schema_path.exists():
        raise SystemExit(f"SQLite schema file not found: {schema_path}")

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    sql_text = schema_path.read_text(encoding="utf-8")

    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(sql_text)
        conn.commit()

    print(f"SQLite schema ready: {sqlite_path}")


if __name__ == "__main__":
    main()
