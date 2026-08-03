# Phase 2C — Evaluation Correction & Multi-Season Backtest

Corrects the methodological defects in the Phase-2B evaluation and adds a
recursive multi-season career backtest. No production integration; Supabase,
frontend, deployment, `data/players/`, and the production predictor are
untouched. Seed 42, reproducible. Artifacts: `results_corrected.json`,
`results_multiseason.json`, `../data/collection/reconciled_counts.json`,
`../data/collection/audit_expanded.json`.

## 1. Blocking defects corrected

| Defect (2B) | Correction (2C) | Evidence |
|---|---|---|
| Partial-season leakage | partial seasons never used as `y_next_*`; transitions into a partial next season censored; partial last season right-censored for continuation | `dataset_corrected`; **0** partial rows used as targets (test) |
| Loose continuation | `y_continue_next_season` = eligible pro domestic-league season in the immediately **consecutive** canonical season; retired→0; active/unknown→null; separate `y_ever_returns` | tests; removed-row counts below |
| Inferred `active` | **sourced** `career_status` from Wikidata (P54 memberships, P570 death) + last sourced season → active 102 / retired 70 / inactive 8 | `career_status.py` |
| Amateur/cameo rows | `model_eligible` / `competition_level` / `exclusion_reason`; excluded from targets & continuation | 2 excluded: Scholes/Royton Town (amateur), Roberto Carlos/Delhi Dynamos (cameo) |
| Start-year chronology | `seasons_consecutive` handles split/calendar/transition; `season_end_year` stored | 6 chronology tests |
| Row-level bootstrap + selection bias | **player-cluster paired bootstrap**; every model reported independently; **time-aware nested selection** (select on val era, report on held-out test era) | §3 |
| Unknown leagues | reviewed `league_overrides.json` (Riquelme→La Liga, Lahm→Bundesliga) | 0 unresolved leagues |
| Count inconsistencies | all counts generated from final artifacts | `reconciled_counts.json` |

**Rows removed / censored** (from `results_corrected.json`): ineligible
seasons 2; regression targets dropped for partial-next 30 and for
non-consecutive (gap) next 12; continuation censored for ongoing-partial-next 30
and for active/unknown last season 110.

## 2. Reconciled dataset counts (from artifacts)

180 players; **3,143 atomic rows**; **2,996 canonical player-seasons**;
2,994 model-eligible feature rows. Coarse position DEF 55 / MID 65 / FWD 30 /
WIDE 30; fine CB 30, FB 25, DM 25, CM 30, AM 10, WNG 30, FW 30 (= roster
sections). Career status active 102 / retired 70 / inactive 8. Partial
(ongoing) seasons 30.

## 3. Corrected one-step evaluation (LOPO, player-cluster bootstrap)

Every candidate reported independently; Δ = naive MAE − model MAE (positive =
model better); CI and P(beats) from the **player-cluster paired bootstrap**.

**Next appearances** (n=2,772; naive 7.01, age+pos 6.22):
| model | MAE | Δ vs naive | 95% CI | P(beats naive) |
|---|---|---|---|---|
| ridge | 5.71 | +1.30 | [1.12, 1.46] | 1.00 |
| histgb | 5.71 | +1.29 | [1.11, 1.46] | 1.00 |
| poisson | 5.72 | +1.29 | [1.11, 1.46] | 1.00 |
| randomforest | 5.84 | +1.17 | [0.97, 1.36] | 1.00 |

Time-aware nested selection: chose ElasticNet on the validation era → **held-out
test MAE 5.96 vs naive 6.56**.

**Next goals** (n=2,772; naive 3.46):
| model | MAE | Δ vs naive | 95% CI | P(beats) |
|---|---|---|---|---|
| histgb_poisson | 3.03 | +0.43 | [0.33, 0.53] | 1.00 |
| ridge | 3.04 | +0.42 | [0.33, 0.52] | 1.00 |
| poisson | 3.25 | +0.21 | [0.08, 0.34] | 0.999 |

Time-aware: chose HistGB-Poisson → **held-out test MAE 2.89 vs naive 3.34**.

**Next goals/appearance** (naive 0.112): ridge/histgb 0.098 (P beats 1.00);
ElasticNet/Poisson do **not** beat naive (reported honestly — no cherry-picking).

**Verdict (one-step):** appearances and goals beat the naive baseline with
player-cluster CIs excluding zero and P(beats)=1.0, and the improvement survives
honest time-aware held-out model selection. This is robust.

## 4. Continuation / retirement evaluation

n=2,854 rows; **82 retirement events** (continue rate 0.971; base-rate Brier
0.0279).

- ROC-AUC **0.938**; **retirement PR-AUC 0.333** (the honest rare-event metric).
- Brier (player-grouped OOF): raw 0.0235, **Platt 0.0249**, isotonic 0.0233 —
  all **beat** the base-rate Brier (0.0279), but only modestly. Calibration
  slope: raw 0.79 (over-confident), **Platt 0.98** (well-calibrated), iso 0.73.
- Operational retirement detection is **weak**: at threshold 0.5, precision
  0.43 / **recall 0.18** (15 of 82 caught, 67 missed); lower thresholds raise
  precision but drop recall further.
- Retirements concentrate at 34+ (66 of 82; recall 0.23 there); younger
  retirements are essentially undetected (recall 0). By position, recall ranges
  0.09 (DEF) – 0.36 (WIDE).

**Verdict (continuation):** probabilities are calibrated (Platt) and beat the
base rate, and ranking is good (AUC 0.94), but **operational retirement-event
detection is weak** (PR-AUC 0.33, recall 0.18). Not "excellent"; usable only as
a soft age-driven survival signal.

## 5. Multi-season recursive backtest

210 trajectories (retired players, ≥5 seasons, 3 cutoffs each), models trained
with the player held out; recursion terminates on continuation probability;
constraints enforced.

**Cumulative appearance MAE by horizon** (vs baselines):
| horizon | model | naive age-curve | persistence |
|---|---|---|---|
| 1 | 5.77 | 5.91 | 6.44 |
| 3 | 13.56 | 13.72 | 17.85 |
| 5 | 22.36 | 23.61 | 32.64 |

Cumulative goal MAE: h1 3.4, h3 8.1, h5 12.3. Remaining-career-length error
**3.55 seasons**; retirement-age error **2.85 years**.

Constraint checks (all clean): **0** negative counts, **0** appearances-cap
violations (cap 60), **0** seasons after modelled retirement, interval width
**monotonically widening** with horizon.

**Verdict (multi-season):** the recursive model clearly beats previous-season
persistence (−10% to −32%), but **only marginally beats a naive population
age-curve** (−2% to −5%). For full-career trajectory prediction, Tier A adds
little over "apply the average ageing curve and stop around the typical
retirement age." Retirement-timing error (~2.9 yrs) and remaining-length error
(~3.6 seasons) are usable but coarse.

## 6. Independent source audit (expanded)

`audit_expanded.json`: **45 players, 797 season values** re-extracted directly
from the cited Wikipedia source cells and corroborated against the collected
atomic rows — **797/797 (100%), 0 mismatches**, including identity overrides.
Combined with the 22 human-verified players in `MANUAL_COLLECTION_AUDIT.md`
(0 mismatches), the dataset is source-accurate for Tier-A fields.

## 7. Tests

64 tests pass (32 model_feasibility incl. 21 Phase-2C, 19 collection, 10
acquisition, 3 existing). Phase-2C tests cover: partial-target exclusion,
right-censoring, active/retired/unknown status, career gaps, comeback seasons,
amateur-cameo exclusion, split-year / calendar-year / calendar→split chronology,
player-cluster bootstrap, recursive forecasting, no future leakage,
non-negative outputs, trajectory termination, and widening uncertainty.

## 8. Final decision

Checking the production-integration criteria:

| Criterion | Result |
|---|---|
| corrected one-step models beat baselines | **Yes** (apps +1.30, goals +0.43) |
| paired player-cluster intervals support it | **Yes** (CIs exclude 0; P(beats)=1.0; held-out test confirms) |
| continuation beats base-rate Brier | **Yes, but modest** (Platt 0.0249 < 0.0279) |
| retirement detection operationally useful | **No** (PR-AUC 0.33; recall 0.18 at thr 0.5) |
| 3- & 5-season trajectories beat naive baselines | **Only marginally** (beat persistence clearly; beat age-curve by 2–5%) |
| cumulative goals/appearances realistic | **Yes** (constraints clean) |
| all report counts consistent | **Yes** (generated from artifacts) |
| all tests pass | **Yes** (64/64) |

### Recommendation: **NO-GO for production integration of the career-trajectory
model; conditional GO for a one-step appearances/goals model.**

- The **one-step** appearances and goals models are validated: they beat naive
  baselines robustly (player-cluster CIs, honest held-out selection) and produce
  realistic, non-negative outputs. A one-step Tier-A predictor is defensible.
- The application's actual product — **full future-career trajectories** — is
  **not** yet supported by Tier A: recursive 3/5-season forecasts only
  marginally beat a population age-curve, and **retirement-event detection is
  weak** (PR-AUC 0.33, recall 0.18). Shipping career trajectories on this signal
  would largely reproduce a naive ageing curve while implying more.

**What would change the decision:** the limiting factor is again Tier B/C —
minutes, starts, shots/xG, and (critically) injury/availability data — which
drive both goal accuracy and retirement/availability timing and are not
obtainable from free respectful sources. Acquiring those is the path to a
career-trajectory model that meaningfully beats the age-curve.

**Not done (per stop conditions):** no production artifact trained/exported, no
Supabase/frontend/deploy changes, no predictor replacement, no goalkeeper work.
Awaiting approval.
