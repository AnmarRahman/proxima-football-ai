"""Phase 3A / 3A.1 / 3A.2 tests: artifact integrity + trust, dataset provenance,
CONDITIONAL interval selection/suppression, structured error contract, strict
scope + season validation, partial policy, immutability, and determinism. The
real CLIs are exercised via subprocess so the JSON-only-stdout / exit-code
contract is verified end to end. Training-based tests are kept to a minimum."""

import copy
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
ART = BACKEND / "model_artifacts" / "tier_a_v1"
TRAIN = BACKEND / "train_production_models.py"
PREDICT = BACKEND / "predict_next_season.py"
DATASET = BACKEND / "data" / "collected_player_seasons.csv"
# small committed fixtures (bulk inference_inputs/ is dev-generated + gitignored)
INPUTS = Path(__file__).resolve().parent / "fixtures"
PY = sys.executable
sys.path.insert(0, str(BACKEND / "model_feasibility"))

ARTIFACT_FILES = ["appearances_model.joblib", "goals_model.joblib",
                  "appearances_interval.joblib", "goals_interval.joblib",
                  "feature_schema.json", "model_manifest.json", "model_card.md",
                  "training_metrics.json", "manifest.sha256"]


def run(cmd, stdin=None):
    # errors="replace": the child logs to stderr under the OS locale (cp1252 on
    # Windows -> en-dash season strings become 0x96); JSON stdout stays ASCII.
    return subprocess.run([PY] + cmd, capture_output=True, text=True, input=stdin,
                          encoding="utf-8", errors="replace", cwd=str(REPO))


def predict(player_path, artifact_dir=ART, extra=None):
    return run([str(PREDICT), "--artifact-dir", str(artifact_dir),
                "--player-json", str(player_path)] + (extra or []))


def load_input(pid):
    return json.loads((INPUTS / f"{pid}.json").read_text(encoding="utf-8"))


def write_tmp(obj):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(obj, f); f.close()
    return f.name


def err_code(r):
    return json.loads(r.stdout)["error"]["code"]


class ArtifactTrustTests(unittest.TestCase):
    def test_all_artifacts_exist(self):
        for f in ARTIFACT_FILES:
            self.assertTrue((ART / f).exists(), f"missing {f}")

    def test_manifest_hashes_match_files(self):
        man = json.loads((ART / "model_manifest.json").read_text(encoding="utf-8"))
        for name, expected in man["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((ART / name).read_bytes()).hexdigest(), expected)

    def test_expected_digest_ok_and_mismatch(self):
        good = (ART / "manifest.sha256").read_text().strip()
        self.assertEqual(predict(INPUTS / "erling-haaland.json",
                                 extra=["--expected-manifest-sha256", good]).returncode, 0)
        bad = predict(INPUTS / "erling-haaland.json", extra=["--expected-manifest-sha256", "dead"])
        self.assertEqual(err_code(bad), "MANIFEST_DIGEST_MISMATCH")

    def test_hash_mismatch_corrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            for f in ARTIFACT_FILES:
                shutil.copy(ART / f, Path(tmp) / f)
            (Path(tmp) / "appearances_model.joblib").write_bytes(b"corrupt")
            self.assertEqual(err_code(predict(INPUTS / "erling-haaland.json", artifact_dir=tmp)),
                             "HASH_MISMATCH")

    def test_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(err_code(predict(INPUTS / "erling-haaland.json", artifact_dir=tmp)),
                             "MISSING_MANIFEST")


class ConditionalIntervalTests(unittest.TestCase):
    def test_nested_policy_report_schema(self):
        m = json.loads((ART / "training_metrics.json").read_text(encoding="utf-8"))
        blob = json.dumps(m)
        self.assertNotIn("actual_holdout_coverage", blob)
        self.assertNotIn("interval_outer_holdout_coverage", blob)   # replaced in 3A.3
        for tgt in ("appearances", "goals"):
            d = m[tgt]
            self.assertIn("final_policy_method", d)
            self.assertIn("final_policy_selection_protocol", d)
            self.assertIn("policy_outer_coverage_when_emitted", d)
            self.assertIn("policy_outer_interval_emission_rate", d)
            self.assertIn("policy_outer_mean_width_when_emitted", d)
            self.assertEqual(sum(d["selected_method_frequency"].values()), 5)  # one per outer fold
            poe = d["policy_outer_evaluation"]
            for key in ("overall", "by_position", "by_age", "by_pred_band",
                        "suppression_rate", "point_mae_all_rows"):
                self.assertIn(key, poe)

    def test_availability_acceptance_pass(self):
        m = json.loads((ART / "training_metrics.json").read_text(encoding="utf-8"))
        for tgt in ("appearances", "goals"):
            self.assertTrue(m[tgt]["policy_outer_availability_all_pass"], f"{tgt} availability failed")

    def test_position_specific_interval(self):
        # goals uses mondrian_pos -> DEF and FWD intervals differ (position-specific)
        vd = json.loads(predict(INPUTS / "virgil-van-dijk.json").stdout)["goals"]
        ha = json.loads(predict(INPUTS / "erling-haaland.json").stdout)["goals"]
        self.assertEqual(vd["interval"]["method"], "mondrian_pos")
        vd_w = vd["interval"]["upper"] - vd["interval"]["lower"]
        ha_w = ha["interval"]["upper"] - ha["interval"]["lower"]
        self.assertNotEqual(vd_w, ha_w)                 # FWD interval wider than DEF

    def test_suppressed_band_returns_null_with_reason(self):
        # appearances low predicted bands (0-15 / 16-25) are suppressed; Modric in
        # latest-completed mode predicts a low appearance count -> null interval.
        o = json.loads(predict(INPUTS / "luka-modric.json",
                               extra=["--prediction-point", "latest-completed"]).stdout)
        self.assertIsNone(o["appearances"]["interval"])
        self.assertIn("interval_unavailable_reason", o["appearances"])

    def test_interval_selection_uses_only_pred_and_position(self):
        import conditional
        params = {"method": "mondrian_pos", "mondrian": True, "scaled": False, "cap": None,
                  "global_q": 5.0, "position_q": {"FWD": 8.0, "DEF": 2.0}, "target_kind": "goals",
                  "suppressed_positions": [], "suppressed_pred_bands": []}
        iv, _ = conditional.runtime_interval(params, 20.0, "FWD")       # no actual y used
        self.assertEqual(iv, (12.0, 28.0))

    def test_insufficient_group_falls_back_to_global(self):
        import conditional
        params = {"method": "mondrian_pos", "mondrian": True, "scaled": False, "cap": None,
                  "global_q": 5.0, "position_q": {"FWD": None}, "target_kind": "goals",
                  "suppressed_positions": [], "suppressed_pred_bands": []}
        iv, _ = conditional.runtime_interval(params, 10.0, "FWD")       # FWD q None -> global 5
        self.assertEqual(iv, (5.0, 15.0))

    def test_non_negative_and_capped(self):
        o = json.loads(predict(INPUTS / "erling-haaland.json").stdout)
        for k in ("appearances", "goals"):
            self.assertGreaterEqual(o[k]["expected"], 0)
            if o[k]["interval"]:
                self.assertGreaterEqual(o[k]["interval"]["lower"], 0)
        if o["appearances"]["interval"]:
            self.assertLessEqual(o["appearances"]["interval"]["upper"], 60)


class ScopeAndSeasonValidationTests(unittest.TestCase):
    def _expect(self, obj, code):
        self.assertEqual(err_code(predict(write_tmp(obj))), code)

    def test_missing_top_level_scope_rejected(self):
        p = load_input("erling-haaland"); p.pop("stat_scope", None)
        self._expect(p, "INVALID_INPUT")

    def test_per_season_scope_rejected(self):
        p = load_input("erling-haaland"); p["seasons"][-1]["stat_scope"] = "all_competitions"
        self._expect(p, "INVALID_INPUT")

    def test_end_year_mismatch_rejected(self):
        p = load_input("erling-haaland"); p["seasons"][-1]["season_end_year"] += 5
        self._expect(p, "INVALID_INPUT")

    def test_duplicate_canonical_rejected(self):
        p = load_input("erling-haaland"); p["seasons"].append(copy.deepcopy(p["seasons"][-1]))
        self._expect(p, "INVALID_INPUT")

    def test_non_integer_year_rejected(self):
        p = load_input("erling-haaland"); p["seasons"][-1]["season_start_year"] = "2025"
        self._expect(p, "INVALID_INPUT")


class StatusAndRejectionTests(unittest.TestCase):
    def test_active_ok(self):
        self.assertEqual(predict(INPUTS / "erling-haaland.json").returncode, 0)

    def test_non_active_rejected(self):
        for status in (None, "unknown", "inactive", "retired"):
            p = load_input("erling-haaland")
            p.pop("career_status") if status is None else p.update(career_status=status)
            self.assertEqual(err_code(predict(write_tmp(p))), "NOT_ACTIVE", status)

    def test_goalkeeper_rejected(self):
        p = load_input("erling-haaland"); p["coarse_group"] = "GK"; p["primary_position"] = "goalkeeper"
        self.assertEqual(err_code(predict(write_tmp(p))), "GOALKEEPER")

    def test_insufficient_history(self):
        p = load_input("erling-haaland"); p["seasons"] = p["seasons"][:1]
        self.assertEqual(err_code(predict(write_tmp(p))), "INSUFFICIENT_HISTORY")


class PartialPolicyTests(unittest.TestCase):
    def test_partial_latest_rejected_by_default(self):
        self.assertEqual(err_code(predict(INPUTS / "luka-modric.json")), "PARTIAL_LATEST_SEASON")

    def test_latest_completed_with_partial(self):
        r = predict(INPUTS / "luka-modric.json", extra=["--prediction-point", "latest-completed"])
        self.assertEqual(r.returncode, 0)
        self.assertTrue(any("ongoing" in w.lower() for w in json.loads(r.stdout)["limitations"]))

    def test_latest_completed_without_partial_rejected(self):
        # Haaland's latest season is completed -> latest-completed must reject
        r = predict(INPUTS / "erling-haaland.json", extra=["--prediction-point", "latest-completed"])
        self.assertEqual(err_code(r), "NO_PARTIAL_SEASON")


class OutputContractTests(unittest.TestCase):
    def test_json_only_stdout(self):
        o = json.loads(predict(INPUTS / "erling-haaland.json").stdout)
        self.assertEqual(o["player_id"], "erling-haaland")

    def test_reproducible(self):
        a = json.loads(predict(INPUTS / "erling-haaland.json").stdout)
        b = json.loads(predict(INPUTS / "erling-haaland.json").stdout)
        a["model"].pop("generated_at"); b["model"].pop("generated_at")
        self.assertEqual(a, b)

    def test_stdin_supported(self):
        raw = (INPUTS / "erling-haaland.json").read_text(encoding="utf-8")
        r = run([str(PREDICT), "--artifact-dir", str(ART)], stdin=raw)
        self.assertEqual(json.loads(r.stdout)["player_id"], "erling-haaland")


class ImmutabilityTests(unittest.TestCase):
    def test_release_artifact_is_clean_and_releasable(self):
        # the committed release artifact must be a clean, unforced, releasable build
        # (the --force/-allow-dirty -> releasable=false property is covered fast by
        # CleanBuildContaminationTests.release_decision).
        man = json.loads((ART / "model_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(man["releasable"])
        self.assertFalse(man["forced_overwrite"])
        self.assertFalse(man["git_dirty"])

    def test_existing_version_refused_without_force(self):
        data_hash = hashlib.sha256(DATASET.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "art"; out.mkdir()
            (out / "model_manifest.json").write_text(json.dumps(
                {"model_version": "tier-a-v1", "training_csv_sha256": data_hash,
                 "artifact_sha256": {}}), encoding="utf-8")
            r = run([str(TRAIN), "--dataset", str(DATASET), "--output-dir", str(out),
                     "--model-version", "tier-a-v1", "--allow-dirty"])   # no --force
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("immutable", (r.stdout + r.stderr).lower())


class CleanBuildContaminationTests(unittest.TestCase):
    def _git(self, args, cwd):
        return subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)

    def test_staging_dir_ignored_completed_version_not(self):
        ignored = self._git(["check-ignore",
                             "backend/python/model_artifacts/tier_a_v1.build-x/f"], REPO)
        self.assertEqual(ignored.returncode, 0)          # staging dir IS ignored
        tracked = self._git(["check-ignore",
                            "backend/python/model_artifacts/tier_a_v1/model_card.md"], REPO)
        self.assertNotEqual(tracked.returncode, 0)       # completed version NOT ignored

    def test_temp_repo_cleanliness_and_release_decision(self):
        sys.path.insert(0, str(BACKEND))
        import train_production_models as TP
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._git(["init"], tmp)
            self._git(["config", "user.email", "t@t.t"], tmp)
            self._git(["config", "user.name", "t"], tmp)
            (tmp / ".gitignore").write_text("art/*.build-*/\n", encoding="utf-8")
            (tmp / "src.py").write_text("x=1\n", encoding="utf-8")
            self._git(["add", "-A"], tmp)
            self._git(["commit", "-m", "init"], tmp)
            self.assertFalse(TP.git_info(cwd=tmp)[1])     # (1) clean build -> not dirty
            # (2) creating the ignored staging dir does not change cleanliness
            (tmp / "art").mkdir(); (tmp / "art" / "v.build-1").mkdir()
            (tmp / "art" / "v.build-1" / "f").write_text("x", encoding="utf-8")
            self.assertFalse(TP.git_info(cwd=tmp)[1])
            # (3) a real tracked modification -> dirty -> release refused
            (tmp / "src.py").write_text("x=2\n", encoding="utf-8")
            self.assertTrue(TP.git_info(cwd=tmp)[1])
            self.assertFalse(TP.release_decision(True, False, False)[0])   # refused
            # (4) an unrelated untracked source file -> dirty -> refused
            self._git(["checkout", "--", "src.py"], tmp)
            (tmp / "extra.py").write_text("y=1\n", encoding="utf-8")
            self.assertTrue(TP.git_info(cwd=tmp)[1])
        # release_decision matrix
        self.assertEqual(TP.release_decision(False, False, False), (True, True))  # clean -> releasable
        self.assertFalse(TP.release_decision(True, True, False)[1])   # (5) --allow-dirty dev -> not releasable
        self.assertFalse(TP.release_decision(False, False, True)[1])  # --force -> not releasable


class DatasetAndDeterminismTests(unittest.TestCase):
    def test_dataset_hash_matches_manifest(self):
        man = json.loads((ART / "model_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(man["training_csv_sha256"], hashlib.sha256(DATASET.read_bytes()).hexdigest())

    def test_dataset_is_actual_training_source_and_deterministic(self):
        # one fresh train on a SUBSET proves --dataset is the source; a fresh train
        # on the FULL set must reproduce the deployed metrics (determinism).
        rows = list(csv.DictReader(open(DATASET, encoding="utf-8")))
        keep = sorted({r["player_id"] for r in rows})[:60]
        with tempfile.TemporaryDirectory() as tmp:
            sub_csv = Path(tmp) / "subset.csv"
            with open(sub_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader()
                for r in rows:
                    if r["player_id"] in keep:
                        w.writerow(r)
            out = Path(tmp) / "sub"
            r = run([str(TRAIN), "--dataset", str(sub_csv), "--output-dir", str(out),
                     "--model-version", "tier-a-v1", "--allow-dirty"])
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            subman = json.loads((out / "model_manifest.json").read_text(encoding="utf-8"))
            full = json.loads((ART / "model_manifest.json").read_text(encoding="utf-8"))
            self.assertLess(subman["input_row_count"], full["input_row_count"])
            self.assertNotEqual(subman["training_csv_sha256"], full["training_csv_sha256"])

            full_out = Path(tmp) / "full"
            r2 = run([str(TRAIN), "--dataset", str(DATASET), "--output-dir", str(full_out),
                      "--model-version", "tier-a-v1", "--allow-dirty"])
            self.assertEqual(r2.returncode, 0, r2.stderr[-400:])
            fm = json.loads((full_out / "training_metrics.json").read_text(encoding="utf-8"))
            deployed = json.loads((ART / "training_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(fm["appearances"]["grouped_oof_mae"],
                             deployed["appearances"]["grouped_oof_mae"])
            self.assertEqual(fm["goals"]["policy_outer_coverage_when_emitted"],
                             deployed["goals"]["policy_outer_coverage_when_emitted"])
            self.assertEqual(fm["goals"]["selected_method_frequency"],
                             deployed["goals"]["selected_method_frequency"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
