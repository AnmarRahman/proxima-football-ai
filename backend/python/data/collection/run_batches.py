"""Batched Tier-A collection orchestrator.

Collects the outfield roster in batches of 25, validating each player and each
batch. Valid players go to collected_players/; players with any validation error
are quarantined to collection_quarantine/ (never described as complete). A
per-batch report is written to collection_reports/.

A batch is a SYSTEMIC failure (stops the run) if a large fraction of the batch
is quarantined for source/normalization reasons; isolated problem players are
quarantined without blocking the rest.

Usage:
  python run_batches.py --batch N        # run one batch (1-indexed)
  python run_batches.py --all            # run every batch in sequence
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
sys.path.insert(0, str(HERE))

from roster import parse_outfield_roster            # noqa: E402
from identity import WikidataIdentity               # noqa: E402
from collect import collect_player                  # noqa: E402
import sys as _sys
_sys.path.insert(0, str(DATA / "acquisition"))
from sources.wikipedia_source import WikipediaSource  # noqa: E402

COLLECTED = DATA / "collected_players"
QUARANTINE = DATA / "collection_quarantine"
REPORTS = DATA / "collection_reports"
for d in (COLLECTED, QUARANTINE, REPORTS):
    d.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 25
SYSTEMIC_QUARANTINE_FRACTION = 0.5     # > this share quarantined => systemic stop


def run_batch(batch_no, players, wiki, wd):
    start = (batch_no - 1) * BATCH_SIZE
    chunk = players[start:start + BATCH_SIZE]
    if not chunk:
        return None

    collected, quarantined = [], []
    warn_count = 0
    for entry in chunk:
        ident = wd.resolve(entry["name"])
        record, errors, warnings = collect_player(ident, entry, wiki)
        warn_count += len(warnings)
        pid = record.get("player_id") or entry["name"].lower().replace(" ", "-")
        if errors:
            record["quarantine_reason"] = errors
            record["warnings"] = warnings
            record.setdefault("coverage", {})["tier_a_complete"] = False
            (QUARANTINE / f"{pid}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            quarantined.append({"player_id": pid, "requested_name": entry["name"],
                                "reasons": errors})
        else:
            record["warnings"] = warnings
            (COLLECTED / f"{pid}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            collected.append({"player_id": pid, "name": record["name"],
                              "seasons": record["coverage"]["senior_seasons"],
                              "warnings": len(warnings)})

    frac_q = len(quarantined) / len(chunk)
    systemic = frac_q > SYSTEMIC_QUARANTINE_FRACTION
    report = {
        "batch": batch_no, "attempted": len(chunk),
        "collected": len(collected), "quarantined": len(quarantined),
        "quarantine_fraction": round(frac_q, 3),
        "systemic_failure": systemic,
        "warnings_total": warn_count,
        "collected_players": collected,
        "quarantined_players": quarantined,
        "requests": {
            "wikipedia": {"total": wiki.http.n_requests, "cache_hit_rate": wiki.http.cache_hit_rate},
            "wikidata": {"total": wd.http.n_requests, "cache_hit_rate": wd.http.cache_hit_rate},
        },
        "gate_ok": not systemic,
    }
    (REPORTS / f"batch_{batch_no:02d}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_batch_md(report)
    return report


def _write_batch_md(r):
    lines = [f"# Collection Batch {r['batch']:02d}", "",
             f"- attempted: {r['attempted']}",
             f"- collected: {r['collected']}",
             f"- quarantined: {r['quarantined']} ({r['quarantine_fraction']*100:.0f}%)",
             f"- systemic failure: {r['systemic_failure']}  (gate {'OK' if r['gate_ok'] else 'STOP'})",
             f"- warnings: {r['warnings_total']}",
             f"- requests: wiki {r['requests']['wikipedia']['total']} "
             f"(cache {r['requests']['wikipedia']['cache_hit_rate']}), "
             f"wikidata {r['requests']['wikidata']['total']} "
             f"(cache {r['requests']['wikidata']['cache_hit_rate']})", "",
             "## Collected", ""]
    for c in r["collected_players"]:
        lines.append(f"- {c['player_id']} ({c['seasons']} seasons"
                     + (f", {c['warnings']} warnings" if c['warnings'] else "") + ")")
    lines += ["", "## Quarantined", ""]
    for q in r["quarantined_players"]:
        lines.append(f"- {q['player_id']} ({q['requested_name']}): {'; '.join(q['reasons'])}")
    (REPORTS / f"batch_{r['batch']:02d}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    players = parse_outfield_roster()
    n_batches = (len(players) + BATCH_SIZE - 1) // BATCH_SIZE
    wiki = WikipediaSource()
    wd = WikidataIdentity()

    batches = range(1, n_batches + 1) if args.all else [args.batch]
    for b in batches:
        if b is None:
            ap.error("specify --batch N or --all")
        rep = run_batch(b, players, wiki, wd)
        if rep is None:
            print(f"batch {b}: empty")
            continue
        print(f"batch {b:02d}: collected={rep['collected']} quarantined={rep['quarantined']} "
              f"({rep['quarantine_fraction']*100:.0f}%) systemic={rep['systemic_failure']} "
              f"wiki_req={rep['requests']['wikipedia']['total']}")
        if rep["systemic_failure"]:
            print(f"  SYSTEMIC FAILURE in batch {b} -> stopping (per gate).")
            break


if __name__ == "__main__":
    main()
