# Model Card — Tier-A One-Season Predictor (tier-a-v1)

## Intended use
Forecast an eligible ACTIVE outfield player's NEXT domestic-league season
appearances and goals (with empirical intervals) from a COMPLETED latest season.
One-step only.

## Unsupported uses
Retirement age, remaining-career length, full-career trajectories, assists,
ratings, tactical attributes, goalkeepers, or predicting the season AFTER an
ongoing partial season. See PHASE_2C_EVALUATION_REPORT.md.

## Training data
`collected_player_seasons.csv` (SHA-256 2ca0bcb6c786...),
domestic-league appearances/goals only. Trained EXCLUSIVELY from this file
(2996 input rows -> 2772 training rows
after Phase-2C filtering). Youth/reserve/amateur and partial-season targets
excluded; status sourced + right-censored; no predicted data as training data.

## Honest metrics (distinct protocols)
- Grouped OOF MAE (NOT a final test set): appearances 5.714
  vs naive 7.008; goals 3.046 vs 3.461.
- Chronological held-out MAE: appearances 5.962
  (naive 6.562); goals 2.892
  (naive 3.343).
- The deployed model is fit on ALL training rows.

## Prediction intervals (CONDITIONAL conformal, FULLY NESTED policy evaluation)
Nominal coverage 0.8. The interval POLICY
(method + suppression + calibration) is evaluated fully nested: per outer fold
the entire policy is learned on outer-train only and applied to untouched
outer-test. Honest **emitted-only** metrics (suppressed rows excluded):

- appearances: coverage-when-emitted 0.856,
  emission rate 0.731, availability all-pass
  True, method frequency
  {'global': 4, 'mondrian_pos': 1}.
- goals: coverage-when-emitted 0.806, emission
  rate 1.0, availability all-pass
  True, method frequency
  {'mondrian_pos': 4, 'mondrian_pos_scaled': 1}.

The DEPLOYED policy is the FINAL all-data policy (appearances='global',
goals='mondrian_pos'); its parameters are NOT independent test
results (see `final_policy_selection_protocol`).

**Interval availability:**
- Unsupported player groups: **none** (appearances [];
  goals []) — every coarse position is covered.
- **Goals intervals are emitted for every position** (DEF/MID/WIDE/FWD).
- **Appearance intervals are NOT universally available**: they are INTENTIONALLY
  SUPPRESSED for low predicted-output bands
  ['0-15', '16-25'] (predicted appearances 0-15 and 16-25),
  where conditional calibration is insufficient. Those return `"interval": null`
  with a reason; the **point estimate is still returned**.

Lower bounds clipped at 0; appearances capped at 60.
Intervals are EMPIRICAL, not exact probabilities, and EXCLUDE unknown injuries,
transfers, and role changes.

## Artifact trust model
manifest artifact_sha256 detects ACCIDENTAL corruption only. For tamper resistance, verify manifest_sha256 out-of-band via --expected-manifest-sha256 or TIER_A_EXPECTED_MANIFEST_SHA256. joblib/pickle loading can execute code; load only from trusted dirs.

## Known limitations / absent Tier B/C signals
No minutes, starts, shots, xG/xA, or injury/availability data (unavailable from
free respectful sources). Their absence bounds goal accuracy and is why
full-career trajectories are unsupported.

## Provenance & retraining
git_commit 9721c4589075f3953ab1c7758a56af116bd420b8, git_dirty False,
releasable True. Deterministic (seed 42).
Retrain (new --model-version) on any training-CSV change; a clean commit is
required before a release build.
