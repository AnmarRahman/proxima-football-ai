"""Train the validated one-season Tier-A models and save versioned artifacts.

Trains TWO models only (Phase-3A scope): next-season domestic-league appearances
and goals. No trajectories/retirement/remaining-career/continuation. Runtime
inference loads these artifacts and never retrains.

Hardening (Phase 3A.1):
  * trains EXCLUSIVELY from --dataset (bytes hashed == bytes trained);
  * honest interval evaluation via nested player-grouped cross-conformal
    (calibrate inside outer folds, coverage on outer-fold predictions only);
  * deployed interval offsets from cross-conformal residuals over the full data;
  * source provenance (git commit/dirty, source/script/feature-builder hashes);
  * release refuses a dirty worktree unless --allow-dirty;
  * ATOMIC build: assemble in a temp dir, run a fresh-process smoke inference,
    then move into place (a failed run leaves no partial version).

Usage:
  python train_production_models.py \
    --dataset backend/python/data/collected_player_seasons.csv \
    --output-dir backend/python/model_artifacts/tier_a_v1 \
    --model-version tier-a-v1 [--allow-dirty]
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import GroupKFold, cross_val_predict

HERE = Path(__file__).resolve().parent
MF = HERE / "model_feasibility"
sys.path.insert(0, str(MF))

import conditional                                     # noqa: E402
import dataset_corrected as DC                         # noqa: E402
import train as T                                      # noqa: E402
from features import FEATURE_COLUMNS                    # noqa: E402

SEED = 42
NOMINAL_COVERAGE = 0.8
APPS_CAP = 60
TARGET_COL = {"appearances": "y_next_apps", "goals": "y_next_goals"}
CUR_COL = {"appearances": "cur_apps", "goals": "cur_goals"}
REQUIRED_COLUMNS = {"player_id", "canonical_season", "season_start_year",
                    "season_end_year", "season_format", "appearances", "goals",
                    "is_partial", "model_eligible", "career_status", "coarse_group",
                    "stat_scope", "birth_date"}
TARGET_DEFS = {
    "appearances": "next canonical domestic-league season appearances (only when the "
                   "next season is genuinely consecutive, eligible, and not partial)",
    "goals": "next canonical domestic-league season goals (same conditions)",
}
PROVENANCE_SOURCES = ["train_production_models.py", "model_feasibility/feature_builder.py",
                      "model_feasibility/dataset_corrected.py", "model_feasibility/features.py",
                      "model_feasibility/conformal.py", "model_feasibility/chronology.py"]


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mae(y, p):
    return float(np.mean(np.abs(np.asarray(y, float) - np.asarray(p, float))))


def git_info(cwd=None):
    cwd = str(cwd or HERE)

    def g(args):
        return subprocess.check_output(["git"] + args, cwd=cwd,
                                       stderr=subprocess.DEVNULL).decode().strip()
    try:
        commit = g(["rev-parse", "HEAD"])
    except Exception:
        return None, None
    try:
        dirty = bool(g(["status", "--porcelain"]))
    except Exception:
        dirty = None
    return commit, dirty


def release_decision(dirty, allow_dirty, force):
    """(proceed, releasable). A dirty worktree may proceed only with --allow-dirty
    and is never releasable; --force is never releasable."""
    proceed = (dirty is False) or bool(allow_dirty)
    releasable = (dirty is False) and (not force)
    return proceed, releasable


def source_provenance():
    parts = []
    for rel in sorted(PROVENANCE_SOURCES):
        p = HERE / rel
        parts.append(rel.encode() + b"\0" + (p.read_bytes() if p.exists() else b""))
    return {
        "source_tree_sha256": hashlib.sha256(b"\0".join(parts)).hexdigest(),
        "training_script_sha256": sha256_file(HERE / "train_production_models.py"),
        "feature_builder_sha256": sha256_file(MF / "feature_builder.py"),
    }


def validate_dataset(rows, output_dir, data_hash, model_version):
    cols = set(rows[0].keys()) if rows else set()
    missing = REQUIRED_COLUMNS - cols
    if missing:
        raise SystemExit(f"[FAIL] required columns missing: {sorted(missing)}")
    scopes = {r["stat_scope"] for r in rows}
    if scopes != {"domestic_league"}:
        raise SystemExit(f"[FAIL] unsupported stat scopes present: {scopes}")
    dupes = [k for k, c in Counter((r["player_id"], r["canonical_season"]) for r in rows).items() if c > 1]
    if dupes:
        raise SystemExit(f"[FAIL] duplicate canonical player-seasons: {dupes[:5]}")
    manifest_path = Path(output_dir) / "model_manifest.json"
    if manifest_path.exists():
        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        if prev.get("model_version") == model_version and prev.get("training_csv_sha256") != data_hash:
            raise SystemExit("[FAIL] dataset hash changed without a new --model-version")


def make_model(target):
    if target == "appearances":
        return T._linear(ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=SEED, max_iter=5000))
    return HistGradientBoostingRegressor(loss="poisson", random_state=SEED,
                                         max_depth=3, learning_rate=0.08)


def build_training_data(dataset_path, target):
    players = DC.load_players(dataset_path)          # <-- from the DECLARED dataset only
    df, removed = DC.build_frame(players)
    if removed.get("target_from_partial_next_excluded", -1) < 0:
        raise SystemExit("[FAIL] partial-target exclusion did not run")
    col = TARGET_COL[target]
    sub = df[df[col].notna()].reset_index(drop=True)
    if sub.empty:
        raise SystemExit(f"[FAIL] no training rows for {col}")
    return sub, removed


def fit_target(dataset_path, target):
    sub, removed = build_training_data(dataset_path, target)
    col, cur = TARGET_COL[target], CUR_COL[target]
    cap = APPS_CAP if target == "appearances" else None
    X = sub[FEATURE_COLUMNS]
    y = sub[col].to_numpy(float)
    groups = sub["player_id"].to_numpy()
    model = make_model(target)

    # (a) grouped OOF point metrics
    oof = np.clip(cross_val_predict(clone(model), X, y, cv=GroupKFold(5), groups=groups), 0, cap)
    grouped_oof_mae = mae(y, oof)
    naive_mae = mae(y, np.clip(sub[cur].to_numpy(float), 0, None))

    # (b) chronological held-out point metrics
    s = sub.sort_values("season_year").reset_index(drop=True)
    q1, q2 = int(np.quantile(s.season_year, 0.6)), int(np.quantile(s.season_year, 0.8))
    tr, te = s[s.season_year <= q1], s[s.season_year > q2]
    chrono_mae = chrono_naive = None
    if len(te) >= 10:
        cm = clone(model).fit(tr[FEATURE_COLUMNS], tr[col].to_numpy(float))
        chrono_mae = mae(te[col].to_numpy(float), np.clip(cm.predict(te[FEATURE_COLUMNS]), 0, cap))
        chrono_naive = mae(te[col].to_numpy(float), np.clip(te[cur].to_numpy(float), 0, None))

    alpha = 1 - NOMINAL_COVERAGE
    # (c) FULLY NESTED honest policy evaluation: per outer fold the ENTIRE interval
    #     policy (method + suppression + calibration) is learned on outer-train
    #     only and applied to held-out outer-test. Outer-test never influences it.
    policy_outer = conditional.nested_policy_eval(model, sub, FEATURE_COLUMNS, col, cap, alpha,
                                                  target, seed=SEED)

    # (d) FINAL production policy: learned from ALL data via grouped inner CV.
    #     This is the DEPLOYED policy; its numbers are NOT independent test results.
    final_policy = conditional.learn_policy(model, sub, FEATURE_COLUMNS, col, cap, alpha,
                                            target, seed=SEED)

    # (e) final full-data model fit (deployed)
    final_model = clone(model).fit(X, y)

    interval = dict(final_policy)                       # runtime params (final all-data policy)
    interval["interval_nominal_coverage"] = NOMINAL_COVERAGE
    interval["note"] = ("Conditional conformal interval keyed on coarse position + the model's "
                        "predicted band (no future actuals). Policy (method/suppression/"
                        "calibration) is the FINAL all-data policy; honest performance is the "
                        "fully-nested policy_outer_evaluation. EMPIRICAL, not an exact confidence "
                        "probability; excludes injuries/transfers/role changes. Suppressed groups "
                        "return interval=null.")
    o = policy_outer["overall"]
    av = policy_outer["availability_acceptance"]
    metrics = {
        "training_row_count": int(len(y)),
        "grouped_oof_mae": round(grouped_oof_mae, 3),
        "naive_persistence_mae": round(naive_mae, 3),
        "chronological_heldout_mae": round(chrono_mae, 3) if chrono_mae is not None else None,
        "chronological_heldout_naive_mae": round(chrono_naive, 3) if chrono_naive is not None else None,
        # HONEST fully-nested policy metrics (outer-test never influenced the policy):
        "policy_outer_coverage_when_emitted": o["coverage_when_emitted"],
        "policy_outer_interval_emission_rate": o["emission_rate"],
        "policy_outer_mean_width_when_emitted": o["mean_width_when_emitted"],
        "policy_outer_median_width_when_emitted": o["median_width_when_emitted"],
        "policy_outer_suppression_rate": policy_outer["suppression_rate"],
        "policy_outer_point_mae_all_rows": policy_outer["point_mae_all_rows"],
        "policy_outer_availability_all_pass": av["_all_pass"],
        "selected_method_frequency": policy_outer["selected_method_frequency"],
        "unsupported_interval_groups": av["unsupported_interval_groups"],
        "policy_outer_evaluation": policy_outer,        # full by position/age/pred-band
        # FINAL all-data production policy (NOT independent test results):
        "final_policy_method": final_policy["method"],
        "final_policy_selection_protocol": "all-data grouped inner CV; predetermined "
                                           "complexity-order rule; NOT an independent test",
        "final_policy_suppressed_positions": final_policy["suppressed_positions"],
        "final_policy_suppressed_pred_bands": final_policy["suppressed_pred_bands"],
        "interval_nominal_coverage": NOMINAL_COVERAGE,
        "excluded_rows": removed,
    }
    return final_model, interval, metrics


def _smoke_input():
    return {"player_id": "_smoke", "coarse_group": "FWD", "career_status": "active",
            "birth_date": "1996-01-01", "primary_position": "forward",
            "stat_scope": "domestic_league",
            "seasons": [
                {"canonical_season": "2023–24", "season_start_year": 2023, "season_end_year": 2024,
                 "season_format": "split_year", "appearances": 30, "goals": 12,
                 "is_partial": False, "model_eligible": True},
                {"canonical_season": "2024–25", "season_start_year": 2024, "season_end_year": 2025,
                 "season_format": "split_year", "appearances": 32, "goals": 15,
                 "is_partial": False, "model_eligible": True}]}


def smoke_inference(artifact_dir):
    """Fresh-process inference against the just-built artifacts."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(_smoke_input(), tf)
        path = tf.name
    try:
        r = subprocess.run([sys.executable, str(HERE / "predict_next_season.py"),
                            "--artifact-dir", str(artifact_dir), "--player-json", path],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"smoke inference failed (exit {r.returncode}): {r.stdout[:300]} {r.stderr[-300:]}")
        obj = json.loads(r.stdout)
        if "appearances" not in obj or "goals" not in obj:
            raise RuntimeError("smoke inference produced no prediction")
    finally:
        os.unlink(path)


def build_into(stage, dataset, data_hash, rows, model_version, allow_dirty, force,
               commit, dirty, initial_prov):
    # git/source state was captured BEFORE the (ignored) staging dir was created,
    # so the staging dir cannot make a clean build look dirty.
    _, releasable = release_decision(dirty, allow_dirty, force)

    app_model, app_int, app_metrics = fit_target(dataset, "appearances")
    goal_model, goal_int, goal_metrics = fit_target(dataset, "goals")

    # Re-verify the source tree did not change during training, excluding the
    # documented temporary staging path (ignored via .gitignore *.build-*).
    if source_provenance() != initial_prov:
        raise SystemExit("[FAIL] source/data hashes changed during training; aborting build")
    _, dirty_now = git_info()
    if dirty_now and not dirty and not allow_dirty:
        raise SystemExit("[FAIL] tracked source/data changed during training; aborting release")

    joblib.dump(app_model, stage / "appearances_model.joblib")
    joblib.dump(goal_model, stage / "goals_model.joblib")
    joblib.dump(app_int, stage / "appearances_interval.joblib")
    joblib.dump(goal_int, stage / "goals_interval.joblib")
    (stage / "feature_schema.json").write_text(json.dumps({
        "feature_names": FEATURE_COLUMNS, "n_features": len(FEATURE_COLUMNS),
        "ordering": "list order is the exact model input order", "stat_scope": "domestic_league",
    }, indent=2), encoding="utf-8")

    training_metrics = {"seed": SEED, "training_csv_sha256": data_hash,
                        "input_row_count": len(rows),
                        "metric_definitions": {
                            "grouped_oof_mae": "player-grouped out-of-fold point MAE (NOT a final independent test set)",
                            "chronological_heldout_mae": "train early seasons, evaluate latest seasons",
                            "policy_outer_*": "FULLY NESTED policy evaluation: per outer fold the entire interval policy (method+suppression+calibration) is learned on outer-train only and applied to held-out outer-test. Emitted-only coverage excludes suppressed rows.",
                            "final_policy_*": "the DEPLOYED all-data policy; NOT independent test results",
                            "final_fit": "deployed point model is fit on ALL training rows"},
                        "appearances": app_metrics, "goals": goal_metrics}
    (stage / "training_metrics.json").write_text(json.dumps(training_metrics, indent=2), encoding="utf-8")

    artifact_hashes = {name: sha256_file(stage / name) for name in
                       ("appearances_model.joblib", "goals_model.joblib",
                        "appearances_interval.joblib", "goals_interval.joblib",
                        "feature_schema.json")}
    prov = initial_prov
    manifest = {
        "model_version": model_version,
        "data_version": f"collected-tier-a-{data_hash[:12]}",
        "training_csv": Path(dataset).name, "training_csv_sha256": data_hash,
        "input_row_count": len(rows),
        "training_row_count": {"appearances": app_metrics["training_row_count"],
                               "goals": goal_metrics["training_row_count"]},
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit, "git_dirty": dirty, "forced_overwrite": bool(force),
        "source_tree_sha256": prov["source_tree_sha256"],
        "training_script_sha256": prov["training_script_sha256"],
        "feature_builder_sha256": prov["feature_builder_sha256"],
        "releasable": releasable,
        "python_version": platform.python_version(), "sklearn_version": sklearn.__version__,
        "seed": SEED, "feature_names": FEATURE_COLUMNS, "n_features": len(FEATURE_COLUMNS),
        "target_definitions": TARGET_DEFS,
        "model_classes": {"appearances": "ElasticNet (Pipeline: impute+scale+model)",
                          "goals": "HistGradientBoostingRegressor(loss='poisson')"},
        "excluded_rows": app_metrics["excluded_rows"],
        "supported_player_scope": "eligible ACTIVE outfield players with >=2 eligible "
                                  "domestic-league seasons and a COMPLETED latest season; "
                                  "goalkeepers and non-active players are out of scope",
        "supported_outputs": ["next_season_appearances", "next_season_goals",
                              "appearance_interval", "goal_interval"],
        "unsupported_outputs": ["retirement_age", "remaining_career", "full_career_trajectory",
                                "assists", "ratings", "tactical_attributes"],
        "stat_scope": "domestic_league", "appearances_cap": APPS_CAP,
        "artifact_trust_model": "manifest artifact_sha256 detects ACCIDENTAL corruption only. "
                                "For tamper resistance, verify manifest_sha256 out-of-band via "
                                "--expected-manifest-sha256 or TIER_A_EXPECTED_MANIFEST_SHA256. "
                                "joblib/pickle loading can execute code; load only from trusted dirs.",
        "artifact_sha256": artifact_hashes,
    }
    (stage / "model_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest_sha = sha256_file(stage / "model_manifest.json")
    (stage / "manifest.sha256").write_text(manifest_sha + "\n", encoding="utf-8")

    _write_model_card(stage, manifest, training_metrics, app_int, goal_int)
    smoke_inference(stage)                            # fresh-process smoke BEFORE publish
    return manifest_sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(HERE / "data" / "collected_player_seasons.csv"))
    ap.add_argument("--output-dir", default=str(HERE / "model_artifacts" / "tier_a_v1"))
    ap.add_argument("--model-version", default="tier-a-v1")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="permit building from a dirty worktree (development only)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing completed version (development only; "
                         "marks the artifact releasable=false)")
    args = ap.parse_args()

    dataset = Path(args.dataset)
    if not dataset.exists():
        raise SystemExit(f"[FAIL] dataset not found: {dataset}")
    rows = list(csv.DictReader(open(dataset, encoding="utf-8")))
    data_hash = sha256_file(dataset)
    outdir = Path(args.output_dir)
    validate_dataset(rows, outdir, data_hash, args.model_version)

    # IMMUTABILITY: a completed version directory must not be silently overwritten
    existing = outdir / "model_manifest.json"
    if existing.exists():
        prev = json.loads(existing.read_text(encoding="utf-8"))
        completed = "artifact_sha256" in prev
        if completed and prev.get("model_version") == args.model_version and not args.force:
            raise SystemExit(f"[FAIL] version '{args.model_version}' already exists and is "
                             "immutable. Bump --model-version, or use --force for a development "
                             "overwrite (which marks the artifact releasable=false).")
    schema_path = outdir / "feature_schema.json"
    if schema_path.exists():
        prev = json.loads(schema_path.read_text(encoding="utf-8"))["feature_names"]
        if prev != FEATURE_COLUMNS:
            raise SystemExit("[FAIL] feature schema differs from committed schema")

    # Capture git + source state BEFORE creating any generated output, so the
    # (gitignored) staging dir cannot make a clean release look dirty.
    commit, dirty = git_info()
    proceed, _ = release_decision(dirty, args.allow_dirty, args.force)
    if not proceed:
        raise SystemExit("[FAIL] refusing to build a release from a DIRTY worktree. "
                         "Commit changes, or pass --allow-dirty for development builds.")
    initial_prov = source_provenance()

    # ATOMIC build: assemble a NEW dir, smoke-test, and publish only on success.
    # The existing version is never deleted before the replacement is verified.
    stage = Path(tempfile.mkdtemp(prefix=f"{outdir.name}.build-", dir=str(outdir.parent)))
    try:
        print(f"[train] staging build in {stage}", file=sys.stderr)
        manifest_sha = build_into(stage, dataset, data_hash, rows, args.model_version,
                                  args.allow_dirty, args.force, commit, dirty, initial_prov)
        # publish: move verified staged build into place (replace only after success)
        if outdir.exists():
            shutil.rmtree(outdir)
        shutil.move(str(stage), str(outdir))
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)     # no partial artifact left behind
        raise

    m = json.loads((outdir / "training_metrics.json").read_text(encoding="utf-8"))
    def tgt_summary(t):
        d = m[t]
        return {"grouped_oof_mae": d["grouped_oof_mae"], "naive_mae": d["naive_persistence_mae"],
                "policy_outer_coverage_when_emitted": d["policy_outer_coverage_when_emitted"],
                "policy_outer_interval_emission_rate": d["policy_outer_interval_emission_rate"],
                "policy_outer_availability_all_pass": d["policy_outer_availability_all_pass"],
                "selected_method_frequency": d["selected_method_frequency"],
                "final_policy_method": d["final_policy_method"]}
    print(json.dumps({"model_version": args.model_version, "manifest_sha256": manifest_sha,
                      "releasable": json.loads((outdir / "model_manifest.json").read_text())["releasable"],
                      "appearances": tgt_summary("appearances"), "goals": tgt_summary("goals")}))


def _write_model_card(outdir, manifest, metrics, app_int, goal_int):
    a, g = metrics["appearances"], metrics["goals"]
    card = f"""# Model Card — Tier-A One-Season Predictor ({manifest['model_version']})

## Intended use
Forecast an eligible ACTIVE outfield player's NEXT domestic-league season
appearances and goals (with empirical intervals) from a COMPLETED latest season.
One-step only.

## Unsupported uses
Retirement age, remaining-career length, full-career trajectories, assists,
ratings, tactical attributes, goalkeepers, or predicting the season AFTER an
ongoing partial season. See PHASE_2C_EVALUATION_REPORT.md.

## Training data
`{manifest['training_csv']}` (SHA-256 {manifest['training_csv_sha256'][:12]}...),
domestic-league appearances/goals only. Trained EXCLUSIVELY from this file
({manifest['input_row_count']} input rows -> {manifest['training_row_count']['appearances']} training rows
after Phase-2C filtering). Youth/reserve/amateur and partial-season targets
excluded; status sourced + right-censored; no predicted data as training data.

## Honest metrics (distinct protocols)
- Grouped OOF MAE (NOT a final test set): appearances {a['grouped_oof_mae']}
  vs naive {a['naive_persistence_mae']}; goals {g['grouped_oof_mae']} vs {g['naive_persistence_mae']}.
- Chronological held-out MAE: appearances {a['chronological_heldout_mae']}
  (naive {a['chronological_heldout_naive_mae']}); goals {g['chronological_heldout_mae']}
  (naive {g['chronological_heldout_naive_mae']}).
- The deployed model is fit on ALL training rows.

## Prediction intervals (CONDITIONAL conformal, FULLY NESTED policy evaluation)
Nominal coverage {app_int['interval_nominal_coverage']}. The interval POLICY
(method + suppression + calibration) is evaluated fully nested: per outer fold
the entire policy is learned on outer-train only and applied to untouched
outer-test. Honest **emitted-only** metrics (suppressed rows excluded):

- appearances: coverage-when-emitted {a['policy_outer_coverage_when_emitted']},
  emission rate {a['policy_outer_interval_emission_rate']}, availability all-pass
  {a['policy_outer_availability_all_pass']}, method frequency
  {a['selected_method_frequency']}.
- goals: coverage-when-emitted {g['policy_outer_coverage_when_emitted']}, emission
  rate {g['policy_outer_interval_emission_rate']}, availability all-pass
  {g['policy_outer_availability_all_pass']}, method frequency
  {g['selected_method_frequency']}.

The DEPLOYED policy is the FINAL all-data policy (appearances='{a['final_policy_method']}',
goals='{g['final_policy_method']}'); its parameters are NOT independent test
results (see `final_policy_selection_protocol`).

**Interval availability:**
- Unsupported player groups: **none** (appearances {a['unsupported_interval_groups']};
  goals {g['unsupported_interval_groups']}) — every coarse position is covered.
- **Goals intervals are emitted for every position** (DEF/MID/WIDE/FWD).
- **Appearance intervals are NOT universally available**: they are INTENTIONALLY
  SUPPRESSED for low predicted-output bands
  {a['final_policy_suppressed_pred_bands']} (predicted appearances 0-15 and 16-25),
  where conditional calibration is insufficient. Those return `"interval": null`
  with a reason; the **point estimate is still returned**.

Lower bounds clipped at 0; appearances capped at {manifest['appearances_cap']}.
Intervals are EMPIRICAL, not exact probabilities, and EXCLUDE unknown injuries,
transfers, and role changes.

## Artifact trust model
{manifest['artifact_trust_model']}

## Known limitations / absent Tier B/C signals
No minutes, starts, shots, xG/xA, or injury/availability data (unavailable from
free respectful sources). Their absence bounds goal accuracy and is why
full-career trajectories are unsupported.

## Provenance & retraining
git_commit {manifest['git_commit']}, git_dirty {manifest['git_dirty']},
releasable {manifest['releasable']}. Deterministic (seed {manifest['seed']}).
Retrain (new --model-version) on any training-CSV change; a clean commit is
required before a release build.
"""
    (outdir / "model_card.md").write_text(card, encoding="utf-8")


if __name__ == "__main__":
    main()
