"""Inference: predict an eligible ACTIVE outfield player's NEXT domestic-league
season appearances and goals from saved artifacts. Never retrains.

  python predict_next_season.py --artifact-dir <dir> [--player-json f]
      [--prediction-point next|latest-completed] [--expected-manifest-sha256 HEX]
  cat player.json | python predict_next_season.py --artifact-dir <dir>

Contract: JSON is written to STDOUT only; logs go to STDERR. Every expected
failure prints {"error":{"code":..,"message":..}} to stdout and exits non-zero.

SECURITY: joblib/pickle artifacts can execute arbitrary code on load. Load
artifacts only from trusted directories you control. `artifact_sha256` in the
manifest detects ACCIDENTAL corruption; for tamper resistance, supply the
expected manifest digest out-of-band (--expected-manifest-sha256 or the
TIER_A_EXPECTED_MANIFEST_SHA256 env var), which is verified before any joblib is
read.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "model_feasibility"))

MIN_SEASONS = 2
OUTFIELD_GROUPS = {"DEF", "MID", "WIDE", "FWD"}
APPS_INPUT_MAX = 80         # single canonical-season sanity bound for input apps
GOALS_INPUT_MAX = 70        # single canonical-season sanity bound for input goals
SEASON_REQUIRED = ["canonical_season", "season_start_year", "season_end_year",
                   "season_format", "appearances", "goals", "is_partial", "model_eligible"]


def log(msg):
    print(f"[predict] {msg}", file=sys.stderr)


def err(code, message, exit_code=2):
    print(json.dumps({"error": {"code": code, "message": message}}))
    sys.exit(exit_code)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_artifacts(artifact_dir, expected_manifest_sha):
    d = Path(artifact_dir)
    if not d.is_dir():
        err("UNTRUSTED_LOCATION", f"artifact dir not found or not a directory: {d}", 3)
    man_path = d / "model_manifest.json"
    if not man_path.exists():
        err("MISSING_MANIFEST", f"model_manifest.json not found in {d}", 3)
    man_bytes = man_path.read_bytes()
    man_sha = hashlib.sha256(man_bytes).hexdigest()
    if expected_manifest_sha:
        if man_sha.lower() != expected_manifest_sha.strip().lower():
            err("MANIFEST_DIGEST_MISMATCH",
                "manifest SHA-256 does not match the expected trusted digest", 3)
        log("manifest digest verified against trusted value")
    else:
        log("WARNING: no expected manifest digest supplied; only accidental-corruption "
            "detection is active (see --expected-manifest-sha256)")
    try:
        manifest = json.loads(man_bytes)
        artifact_hashes = manifest["artifact_sha256"]
    except Exception as e:
        err("MALFORMED_MANIFEST", f"manifest unreadable: {e}", 3)

    # verify artifact hashes BEFORE loading any joblib (accidental-corruption guard)
    for name, expected in artifact_hashes.items():
        f = d / name
        if not f.exists():
            err("MISSING_ARTIFACT", f"artifact missing: {name}", 3)
        if sha256_file(f) != expected:
            err("HASH_MISMATCH", f"artifact hash mismatch for {name} (corrupted or tampered)", 3)

    schema = json.loads((d / "feature_schema.json").read_text(encoding="utf-8"))
    from features import FEATURE_COLUMNS
    if schema["feature_names"] != FEATURE_COLUMNS:
        err("INCOMPATIBLE_ARTIFACT", "feature schema mismatch between artifact and runtime", 3)

    try:
        import joblib
        return {"manifest": manifest,
                "app_model": joblib.load(d / "appearances_model.joblib"),
                "goal_model": joblib.load(d / "goals_model.joblib"),
                "app_int": joblib.load(d / "appearances_interval.joblib"),
                "goal_int": joblib.load(d / "goals_interval.joblib")}
    except Exception as e:
        err("INCOMPATIBLE_ARTIFACT", f"could not load artifacts (sklearn/joblib mismatch?): {e}", 3)


def next_season_label(canon):
    m = re.match(r"^(\d{4})[–\-/](\d{2,4})$", str(canon))
    if m:
        s = int(m.group(1))
        return f"{s + 1}–{str(s + 2)[-2:]}"
    if re.match(r"^\d{4}$", str(canon)):
        return str(int(canon) + 1)
    return None


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_input(player):
    if not isinstance(player, dict):
        err("MALFORMED_INPUT", "player JSON must be an object")
    if not str(player.get("player_id") or "").strip():
        err("INVALID_INPUT", "player_id is required")
    birth = str(player.get("birth_date") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", birth):
        err("INVALID_INPUT", "birth_date must be an ISO date YYYY-MM-DD")
    coarse = player.get("coarse_group")
    pos = str(player.get("primary_position") or player.get("position_group") or "").lower()
    if "keeper" in pos or player.get("position_group") == "GK" or coarse == "GK":
        err("GOALKEEPER", "goalkeepers are out of scope")
    if coarse not in OUTFIELD_GROUPS:
        err("INVALID_INPUT", f"coarse_group must be one of {sorted(OUTFIELD_GROUPS)}")
    status = player.get("career_status")
    if status != "active":
        err("NOT_ACTIVE", f"career_status must be exactly 'active' (got {status!r}); "
                          "missing/unknown/inactive/retired are rejected")
    # STRICT scope: require an explicit top-level domestic_league (no default)
    if player.get("stat_scope") != "domestic_league":
        err("INVALID_INPUT", "top-level stat_scope must be explicitly 'domestic_league'")
    seasons = player.get("seasons")
    if not isinstance(seasons, list) or not seasons:
        err("INVALID_INPUT", "seasons must be a non-empty array")

    seen = set()
    for i, s in enumerate(seasons):
        if not isinstance(s, dict):
            err("INVALID_INPUT", f"seasons[{i}] must be an object")
        for f in SEASON_REQUIRED:
            if f not in s or s[f] is None:
                err("INVALID_INPUT", f"seasons[{i}] missing required field '{f}'")
        # per-season scope must not mix scopes
        if s.get("stat_scope", "domestic_league") != "domestic_league":
            err("INVALID_INPUT", f"seasons[{i}].stat_scope must be 'domestic_league' (no mixed scopes)")
        if not isinstance(s["is_partial"], bool) or not isinstance(s["model_eligible"], bool):
            err("INVALID_INPUT", f"seasons[{i}] is_partial/model_eligible must be booleans")
        for yf in ("season_start_year", "season_end_year"):
            if not isinstance(s[yf], int) or isinstance(s[yf], bool):
                err("INVALID_INPUT", f"seasons[{i}].{yf} must be an integer")
        fmt, sy, ey = s["season_format"], s["season_start_year"], s["season_end_year"]
        if fmt not in ("split_year", "calendar_year"):
            err("INVALID_INPUT", f"seasons[{i}].season_format must be split_year|calendar_year")
        if fmt == "split_year" and ey != sy + 1:
            err("INVALID_INPUT", f"seasons[{i}]: split_year end year must be start+1 ({sy}->{ey})")
        if fmt == "calendar_year" and ey != sy:
            err("INVALID_INPUT", f"seasons[{i}]: calendar_year end year must equal start ({sy}!={ey})")
        for f in ("appearances", "goals"):
            if not _is_number(s[f]):
                err("INVALID_INPUT", f"seasons[{i}].{f} must be numeric")
            if s[f] < 0:
                err("INVALID_INPUT", f"seasons[{i}].{f} must be non-negative")
        if s["appearances"] > APPS_INPUT_MAX:
            err("INVALID_INPUT", f"seasons[{i}].appearances {s['appearances']} exceeds sanity bound {APPS_INPUT_MAX}")
        if s["goals"] > GOALS_INPUT_MAX:
            err("INVALID_INPUT", f"seasons[{i}].goals {s['goals']} exceeds sanity bound {GOALS_INPUT_MAX}")
        if s["canonical_season"] in seen:
            err("INVALID_INPUT", f"duplicate canonical season '{s['canonical_season']}'")
        seen.add(s["canonical_season"])
    return birth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", required=True)
    ap.add_argument("--player-json")
    ap.add_argument("--prediction-point", choices=["next", "latest-completed"], default="next")
    ap.add_argument("--expected-manifest-sha256",
                    default=os.environ.get("TIER_A_EXPECTED_MANIFEST_SHA256"))
    args = ap.parse_args()

    art = load_artifacts(args.artifact_dir, args.expected_manifest_sha256)
    manifest = art["manifest"]
    log(f"loaded model {manifest['model_version']} (data {manifest['data_version']})")

    try:
        raw = (Path(args.player_json).read_text(encoding="utf-8") if args.player_json
               else sys.stdin.buffer.read().decode("utf-8"))
    except Exception as e:
        err("MALFORMED_INPUT", f"could not read input: {e}")
    try:
        player = json.loads(raw)
    except json.JSONDecodeError as e:
        err("MALFORMED_INPUT", f"invalid player JSON: {e}")

    birth = validate_input(player)
    birth_year = int(birth[:4])
    coarse = player["coarse_group"]

    from chronology import order_seasons, seasons_consecutive
    from feature_builder import feature_row
    from features import FEATURE_COLUMNS
    import conditional
    import pandas as pd

    ordered_all = order_seasons(player["seasons"])
    # overlapping distinct canonical seasons are invalid unless they are the
    # tested calendar->split transition (same start year, end year +1).
    for a, b in zip(ordered_all, ordered_all[1:]):
        if a["canonical_season"] == b["canonical_season"]:
            continue
        overlap = b["season_start_year"] < a["season_end_year"]
        transition = (b["season_start_year"] == a["season_start_year"]
                      and b["season_end_year"] == a["season_end_year"] + 1)
        if overlap and not transition and not seasons_consecutive(a, b):
            err("INVALID_INPUT", f"overlapping seasons {a['canonical_season']} and "
                                 f"{b['canonical_season']} are not a supported transition")

    elig = [s for s in ordered_all if s.get("model_eligible", True)]
    if len(elig) < MIN_SEASONS:
        err("INSUFFICIENT_HISTORY", f"{len(elig)} eligible seasons (need >= {MIN_SEASONS})")

    warnings = ["Domestic-league statistics only",
                "Injuries and transfers are not model inputs",
                "This is a next-season forecast, not a full-career prediction"]

    # ---- partial-season policy ----
    if args.prediction_point == "latest-completed":
        if not elig[-1]["is_partial"]:
            err("NO_PARTIAL_SEASON",
                "--prediction-point latest-completed requires the latest eligible season to be "
                "partial/ongoing, but it is completed. Use the default mode instead.")
        basis = [s for s in elig if not s["is_partial"]]
        if len(basis) < MIN_SEASONS:
            err("INSUFFICIENT_HISTORY",
                f"{len(basis)} completed eligible seasons (need >= {MIN_SEASONS})")
        warnings.append("prediction-point=latest-completed: partial season IGNORED; "
                        "predicting the CURRENTLY ONGOING season from the last completed season")
        warnings.append("Does NOT predict the season after the ongoing partial season")
    else:  # default: latest must be completed
        if elig[-1]["is_partial"]:
            err("PARTIAL_LATEST_SEASON",
                "latest eligible season is partial/ongoing; production requires a COMPLETED "
                "latest season. Re-run with --prediction-point latest-completed to forecast "
                "the ongoing season from the last completed season instead.")
        basis = elig

    if not basis[-1].get("model_eligible", True):
        err("INVALID_INPUT", "the selected prediction-basis season is not model_eligible")
    if len(basis) < 4:
        warnings.append(f"Only {len(basis)} eligible seasons of history")

    apps = [int(s["appearances"]) for s in basis]
    goals = [int(s["goals"]) for s in basis]
    years = [int(s["season_start_year"]) for s in basis]
    i = len(basis) - 1
    latest = basis[i]

    X = pd.DataFrame([feature_row(apps, goals, years, i, birth_year, coarse)], columns=FEATURE_COLUMNS)

    def predict_one(model, params):
        exp = max(0.0, float(model.predict(X)[0]))
        cap = params.get("cap")
        if cap:
            exp = min(cap, exp)
        # conditional interval selection uses ONLY position + point prediction
        iv, reason = conditional.runtime_interval(params, exp, coarse)
        return exp, iv, reason

    def interval_block(exp, iv, reason, params):
        b = {"expected": int(round(exp))}
        if iv is None:
            b["interval"] = None
            b["interval_unavailable_reason"] = reason or "Insufficient conditional calibration"
        else:
            lo, hi = iv
            b["interval"] = {"lower": int(round(lo)), "upper": int(round(hi)),
                             "nominal_coverage": params["interval_nominal_coverage"],
                             "method": params.get("method")}
        return b

    try:
        a_exp, a_iv, a_reason = predict_one(art["app_model"], art["app_int"])
        g_exp, g_iv, g_reason = predict_one(art["goal_model"], art["goal_int"])
    except Exception as e:
        err("PREDICTION_FAILED", f"model prediction failed: {e}", 4)

    out = {
        "player_id": player["player_id"],
        "prediction_scope": "next_domestic_league_season",
        "prediction_point": args.prediction_point,
        "based_on_season": latest.get("canonical_season"),
        "predicted_season": next_season_label(latest.get("canonical_season")),
        "appearances": interval_block(a_exp, a_iv, a_reason, art["app_int"]),
        "goals": interval_block(g_exp, g_iv, g_reason, art["goal_int"]),
        "model": {"version": manifest["model_version"], "data_version": manifest["data_version"],
                  "generated_at": datetime.now(timezone.utc).isoformat()},
        "coverage_metadata": {"eligible_seasons_used": len(basis), "stat_scope": "domestic_league",
                              "career_status": player.get("career_status")},
        "limitations": warnings,
    }
    print(json.dumps(out, ensure_ascii=False))
    log("prediction written to stdout")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:                        # last-resort structured error
        err("PREDICTION_FAILED", f"unexpected failure: {e}", 4)
