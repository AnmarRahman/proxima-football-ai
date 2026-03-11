import argparse
import os
from pathlib import Path

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("psycopg is required. Install backend requirements first.") from exc

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR.parent / "db" / "migrations"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply SQL migrations to Postgres.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Postgres connection string. Defaults to DATABASE_URL env var.",
    )
    return parser.parse_args()


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists schema_migrations (
              version text primary key,
              applied_at timestamptz not null default now()
            )
            """
        )


def has_migration(conn: psycopg.Connection, version: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("select 1 from schema_migrations where version = %s", (version,))
        return cur.fetchone() is not None


def apply_migration(conn: psycopg.Connection, version: str, sql_text: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql_text)
        cur.execute("insert into schema_migrations(version) values (%s)", (version,))


def main() -> None:
    args = parse_args()
    database_url = args.database_url.strip()
    if not database_url:
        raise SystemExit("Missing database url. Set DATABASE_URL or pass --database-url.")

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        raise SystemExit(f"No SQL migrations found in {MIGRATIONS_DIR}")

    with psycopg.connect(database_url) as conn:
        ensure_migrations_table(conn)
        conn.commit()

        for file_path in files:
            version = file_path.name
            if has_migration(conn, version):
                print(f"Skipping {version} (already applied)")
                continue

            sql_text = file_path.read_text(encoding="utf-8")
            apply_migration(conn, version, sql_text)
            conn.commit()
            print(f"Applied {version}")

    print("Migrations complete.")


if __name__ == "__main__":
    main()
