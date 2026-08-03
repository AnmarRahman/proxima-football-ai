"""Import the canonical Tier A CSV and approved model metadata into Postgres."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / "data" / "collected_player_seasons.csv"
DEFAULT_ARTIFACT_DIR = HERE / "model_artifacts" / "tier_a_v1"


def parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Tier A CSV is empty: {csv_path}")
    return rows


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        player_id = str(row.get("player_id") or "").strip().lower()
        if not player_id:
            raise ValueError("Tier A row is missing player_id")
        grouped[player_id].append(row)
    return dict(grouped)


def register_model(cur: psycopg.Cursor, artifact_dir: Path) -> str:
    manifest_path = artifact_dir / "model_manifest.json"
    digest_path = artifact_dir / "manifest.sha256"
    metrics_path = artifact_dir / "training_metrics.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    manifest_sha = digest_path.read_text(encoding="utf-8").strip()
    version = str(manifest["model_version"])

    cur.execute(
        """
        insert into model_versions(
          version, data_version, manifest_sha256, training_csv_sha256,
          source_git_commit, trained_at, approved, metrics, manifest, updated_at
        ) values (%s, %s, %s, %s, %s, %s, true, %s, %s, now())
        on conflict (version) do update set
          data_version = excluded.data_version,
          manifest_sha256 = excluded.manifest_sha256,
          training_csv_sha256 = excluded.training_csv_sha256,
          source_git_commit = excluded.source_git_commit,
          trained_at = excluded.trained_at,
          approved = excluded.approved,
          metrics = excluded.metrics,
          manifest = excluded.manifest,
          updated_at = now()
        """,
        (
            version,
            manifest["data_version"],
            manifest_sha,
            manifest["training_csv_sha256"],
            manifest.get("git_commit"),
            manifest.get("training_timestamp"),
            Jsonb(metrics),
            Jsonb(manifest),
        ),
    )
    return version


def import_players(cur: psycopg.Cursor, grouped: dict[str, list[dict[str, str]]]) -> tuple[int, int]:
    season_count = 0
    for player_id, rows in sorted(grouped.items()):
        meta = rows[0]
        cur.execute(
            """
            insert into ml_players(
              id, name, birth_date, nationality, primary_position, position_group,
              coarse_group, career_status, stat_scope, updated_at
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            on conflict (id) do update set
              name = excluded.name,
              birth_date = excluded.birth_date,
              nationality = excluded.nationality,
              primary_position = excluded.primary_position,
              position_group = excluded.position_group,
              coarse_group = excluded.coarse_group,
              career_status = excluded.career_status,
              stat_scope = excluded.stat_scope,
              updated_at = now()
            """,
            (
                player_id,
                meta["name"],
                meta["birth_date"],
                meta.get("nationality") or None,
                meta.get("primary_position") or None,
                meta.get("position_group") or None,
                meta["coarse_group"],
                meta["career_status"],
                meta["stat_scope"],
            ),
        )

        cur.execute("delete from ml_player_seasons where player_id = %s", (player_id,))
        for row in sorted(rows, key=lambda item: (int(item["season_start_year"]), item["canonical_season"])):
            cur.execute(
                """
                insert into ml_player_seasons(
                  player_id, canonical_season, season_start_year, season_end_year,
                  season_format, appearances, goals, is_partial, model_eligible, source_row
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    player_id,
                    row["canonical_season"],
                    int(row["season_start_year"]),
                    int(row["season_end_year"]),
                    row["season_format"],
                    int(row["appearances"]),
                    int(row["goals"]),
                    parse_bool(row["is_partial"]),
                    parse_bool(row["model_eligible"]),
                    Jsonb(row),
                ),
            )
            season_count += 1

    # The committed release is a complete snapshot. Removing players no longer
    # in it also removes their stale current predictions via foreign keys.
    cur.execute("delete from ml_players where not (id = any(%s))", (list(grouped),))
    return len(grouped), season_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.database_url.strip():
        raise SystemExit("Missing DATABASE_URL or --database-url")
    rows = load_rows(args.csv.resolve())
    grouped = group_rows(rows)

    with psycopg.connect(args.database_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            players, seasons = import_players(cur, grouped)
            version = register_model(cur, args.artifact_dir.resolve())
        conn.commit()

    print(f"Tier A import complete: players={players}, seasons={seasons}, approved_model={version}")


if __name__ == "__main__":
    main()
