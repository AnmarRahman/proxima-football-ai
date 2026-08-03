# Phase 3A / 3A.1 / 3A.2 / 3A.3 — Productionized One-Season Models

Versioned artifacts + a hardened inference contract for the **validated
one-season** predictions only (next-season domestic-league appearances and
goals). No trajectories, retirement, remaining-career, or continuation. Nothing
integrated: Supabase, frontend, GitHub Actions, deployment, `data/players/`, and
the production predictor are untouched. No deploy. Awaiting approval.

## Point models (accepted — NOT retuned)

Appearances → `ElasticNet` pipeline; goals →
`HistGradientBoostingRegressor(loss="poisson")`. Honest point metrics:

| target | grouped-OOF MAE | naive | chronological held-out MAE | naive |
|---|---|---|---|---|
| appearances | 5.71 | 7.01 | 5.96 | 6.56 |
| goals | 3.05 | 3.46 | 2.89 | 3.34 |

## 3A.3 — fully nested interval-policy evaluation (the fix)

**Problem (3A.2):** method selection, suppression, and calibration all inspected
the same outer folds later used for reporting. Changing the inner seed did not
make the outer evaluation independent.

**Fix:** the entire interval **policy** (method + suppression + calibration) is
now learned by `learn_policy()` from a single training set. In
`nested_policy_eval()`, for each outer player-grouped fold the policy is learned
on **outer-train only**, frozen, the point model is fit on outer-train, and the
frozen policy is applied to the **held-out outer-test** players. The outer-test
fold never influences method selection, suppression, fallback, thresholds, or
calibration (proven by tests: mutating outer-test targets leaves the frozen
policy bit-identical). Runtime selects intervals using only coarse position and
the point prediction — never a future actual.

**Inner selection (per outer fold):** methods evaluated in complexity order
(global → mondrian_pos → scaled → mondrian_pos_scaled) via player-grouped inner
folds; the simplest fully-passing method is chosen; ties → narrower width →
simpler. Selected-method frequency across the 5 outer folds is recorded.

**Reporting** replaces `interval_outer_holdout_coverage` with explicit
emitted-only metrics: `policy_outer_coverage_when_emitted`,
`policy_outer_interval_emission_rate`, `policy_outer_mean_width_when_emitted`.
Nominal coverage is never computed over suppressed rows.

## Honest fully-nested results (outer-test never influenced the policy)

### Appearances — method frequency {global: 4, mondrian_pos: 1}; deployed `global`
- **coverage-when-emitted 0.856**, **emission rate 0.731**, mean width 17.4,
  suppression 0.269, point MAE (all rows) 5.71.
- By position (emitted coverage / emission): DEF .84/.67, MID .87/.78,
  WIDE .88/.74, FWD .84/.74 — all coverage ≥0.70, all emission ≥0.60.
- By predicted band: 26-34 cov .87 (emit 1.0), **35+ cov .72 (emit 1.0)**; low
  bands 0-15 and 16-25 are **suppressed** (emit ≈0) → runtime returns
  `"interval": null` with a reason.
- **Availability acceptance: PASS. Unsupported groups: none.**

### Goals — method frequency {mondrian_pos: 4, mondrian_pos_scaled: 1}; deployed `mondrian_pos`
- **coverage-when-emitted 0.806**, **emission rate 1.00** (nothing suppressed),
  mean width 8.9, point MAE 3.05.
- By position: DEF .80, MID .81, WIDE .82, **FWD .80** (the original blocker —
  forwards now covered), all emit 1.0.
- By predicted band: 0-2 .86, 3-7 .83, 8-15 .73, **16+ .79** — all ≥0.70.
- **Availability acceptance: PASS. Unsupported groups: none.**

## Final production policy (separate from the honest evaluation)

The DEPLOYED policy is learned from ALL data via grouped inner CV
(`final_policy_selection_protocol`): appearances = `global` (suppresses predicted
bands 0-15, 16-25); goals = `mondrian_pos` (no suppression). **These final-policy
parameters are NOT independent test results** — the honest performance is the
fully-nested `policy_outer_evaluation` above. Artifact fields:
`policy_outer_evaluation`, `policy_outer_coverage_when_emitted`,
`policy_outer_interval_emission_rate`, `policy_outer_suppression_rate`,
`selected_method_frequency`, `final_policy_selection_protocol`,
`final_policy_method` / suppressed groups, `unsupported_interval_groups`.

Runtime examples: Haaland FWD goals 23 (14–33); van Dijk DEF goals 2 (0–4);
Modric (latest-completed, low predicted appearances) → appearances
`interval: null` (band 0-15 suppressed), goals interval still emitted.

## Availability acceptance criteria — result

| criterion (nominal 80%) | appearances | goals |
|---|---|---|
| overall coverage-when-emitted ∈ [0.75, 0.87] | 0.856 ✓ | 0.806 ✓ |
| per-position coverage ≥ 0.70 | ✓ (≥.84) | ✓ (≥.80) |
| high predicted band coverage ≥ 0.70 | 35+ .72 ✓ | 16+ .79 ✓ |
| overall emission rate ≥ 0.70 | 0.731 ✓ | 1.00 ✓ |
| per-position emission ≥ 0.60 | ✓ (≥.67) | ✓ (1.0) |
| widths practically useful | ~17 apps | ~9 goals |

**All release coverage AND availability criteria pass** for both targets on the
fully-nested honest evaluation, with no unsupported interval subgroups.

## Other hardening (3A.1/3A.2, retained)

Train only from `--dataset`; provenance (git commit/dirty, source/script/
feature-builder hashes) + dirty-worktree release refusal; atomic staged build +
fresh-process smoke; structured `{"error":{"code","message"}}` contract; strict
explicit `stat_scope`; full season type/relationship validation; `career_status
== "active"` required; partial-latest rejected by default, `--prediction-point
latest-completed` requires an actual partial season (else `NO_PARTIAL_SEASON`);
trusted manifest digest verified before joblib load (pickle code-exec risk
documented); immutable versions (`--force` dev-only → `releasable=false`).

## Tests

**102 pass** (7 new Phase-3A.3: outer-test never enters inner selection;
outer-test outcomes never affect suppression; changing outer-test targets leaves
the frozen policy identical; emitted-only coverage excludes suppressed rows;
emission rate correct; method-selection frequency recorded; final all-data policy
separated from outer evaluation; deterministic at seed 42; runtime ignores
actuals — plus 31 Phase-3A/3A.1/3A.2, 39 model_feasibility, 19 collection, 10
acquisition, 3 existing).

## Final report

- **Outer-fold selected methods / frequency:** appearances {global:4,
  mondrian_pos:1}; goals {mondrian_pos:4, mondrian_pos_scaled:1}.
- **Coverage when emitted:** appearances 0.856, goals 0.806.
- **Interval emission rate:** appearances 0.731, goals 1.00.
- **Suppression rate:** appearances 0.269, goals 0.00.
- **Widths (mean/median):** appearances 17.4 / 17.4; goals 8.9 / 7.3.
- **By position/age/predicted band:** in `training_metrics.json` →
  `policy_outer_evaluation`; summarized above.
- **Unsupported interval groups:** none (both targets).
- **All release coverage + availability criteria pass:** **YES** (both targets).
- **Clean commit / retrain approved?** **NO — still required.** `git_dirty=true`,
  the code/data are untracked, and this build used `--allow-dirty --force`, so
  `releasable=false`. A clean commit of code + data + pipeline, then a fresh
  release retrain (no `--allow-dirty`/`--force`), is required before any release.

## Stop

Fully-nested interval policy evaluated and honestly reported; the deployed policy
is separated from the honest outer metrics. No commit, no release retrain, no
integration, no deploy. Awaiting approval; a clean commit + release retrain
remains required before release.
