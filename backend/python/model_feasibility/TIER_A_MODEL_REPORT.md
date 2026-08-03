# Tier-A Model Feasibility Report (Phase 2A)

Question: can the **freely obtainable Tier-A fields** (domestic-league
appearances + goals + identity, collected via the approved Wikimedia pipeline)
produce a model that **meaningfully predicts future outfield-player seasons**,
beating naive baselines?

Scope guardrails honoured: no bulk collection; no changes to production player
JSON, Supabase, frontend, or deployment; Tier-A-only features; missing kept
distinct from zero; provenance preserved; youth seasons excluded; national-team
stats excluded from club targets; goalkeepers out of scope; predictions
non-negative; fixed seed (42); reproducible.

Artifacts: dataset in `data/acquisition/model_feasibility_data/`, code in
`model_feasibility/`, raw metrics in `model_feasibility/results.json`.

---

## 1. Exact pilot roster (20 outfield players)

Chosen from `PLAYER_SCRAPE_ROSTER.md` for diverse positions, eras, career
lengths, and scoring profiles. (Coarse group used for modelling in brackets.)

| Player | Fine pos | Group | Active | Era / profile |
|---|---|---|---|---|
| Erling Haaland | FW | FWD | yes | 2010s–20s, young high scorer |
| Zlatan Ibrahimovic | FW | FWD | no | very long career |
| Thierry Henry | FW | FWD | no | 1990s–2010s |
| Marco van Basten | FW | FWD | no | **early retirement (injury, age 28)**, 1980s–90s |
| Cristiano Ronaldo | WNG | WIDE | yes | 2000s–20s |
| Arjen Robben | WNG | WIDE | no | 2000s–10s |
| Franck Ribery | WNG | WIDE | no | long career |
| David Beckham | WNG | WIDE | no | wide mid, low scorer |
| Kaka | AM | MID | no | attacking mid |
| Francesco Totti | AM | MID | no | one-club, very long |
| Frank Lampard | CM | MID | no | high-scoring midfielder |
| Steven Gerrard | CM | MID | no | box-to-box |
| Luka Modric | CM | MID | yes | long, low scorer |
| Andrea Pirlo | CM | MID | no | deep playmaker |
| Sergio Busquets | DM | MID | yes | very low scorer |
| Virgil van Dijk | CB | DEF | yes | centre-back |
| Sergio Ramos | CB | DEF | yes | high-scoring CB |
| Paolo Maldini | CB | DEF | no | 1980s–2000s, very long |
| Dani Alves | FB | DEF | no | full-back, very long |
| Philipp Lahm | FB | DEF | no | full-back |

Coarse groups: FWD 4, WIDE 4, MID 7, DEF 5. Eras span **1981–2026**.

---

## 2. Players, rows, and coverage

- **20 players**, **407 senior season-year rows** (domestic league).
- **387 rows** have a next season (used for appearances/goals/gpa targets).
- **401 rows** used for continuation (active players' final season censored);
  **14 retirement events** (continuation rate 0.965).
- **292 rows** for the experimental remaining-career target (retired players).
- Reserve/youth rows excluded (e.g. Barcelona B, Sevilla Atlético, Sporting CP
  B, Bryne 2): 11 rows dropped across the roster, logged per player in each
  file's `coverage.dropped_rows`.
- **Scope confirmed domestic-league only**: the Wikipedia parser reads the
  "League" Apps/Goals columns exclusively; every row carries
  `stat_scope: "domestic_league"` and is never mixed with cup/continental/total
  figures. Provenance (`provider=Wikipedia`, url, retrieved_at, supports) is
  stored per player.

Tier-A coverage is effectively **100%** (appearances, goals, position, birth
date, nationality present for all rows); Tier B/C is **0%** (unavailable for
free — see the free-source pilot report).

---

## 3. Target definitions (separate targets, not one vector)

| Target | Definition | Type |
|---|---|---|
| `y_next_apps` | next season's domestic-league appearances | count ≥ 0 |
| `y_next_goals` | next season's domestic-league goals | count ≥ 0 |
| `y_next_gpa` | next season goals ÷ appearances (rows with next apps > 0) | ratio ≥ 0 |
| `y_continue` | 1 if the player records another senior season, else 0 | probability |
| `y_remaining` | number of senior seasons after this one (experimental) | count ≥ 0 |

Censoring: an **active** player's final observed season has unknown
continuation and unknown remaining-career, so those labels are **null**
(excluded), never assumed. Retirement is thus modelled **probabilistically per
season**, not as a fixed age cutoff.

---

## 4. Feature definitions (Tier-A only, leakage-safe)

Per (player, season) using only seasons up to and including that season:
`age`, `age²`, `season_year`, `years_experience`; current `apps`, `goals`,
`gpa`; `career_apps`, `career_goals`, `career_gpa` (to date); **lag 1–5**
appearances and goals; `roll3_apps/goals/gpa` (last-3-season rolling);
`apps_trend3` (availability trend); `delta_apps/goals` (season-over-season
change); coarse position one-hots (FWD/WIDE/MID/DEF).

**Missing ≠ zero:** lag/delta values that don't exist yet are `NaN` and carry an
explicit `*_missing` indicator; a genuine 0-appearance season (e.g. an
injury year) is stored as `0`, and the unit test
`test_real_zero_season_is_zero_not_missing` locks this in.

---

## 5. Leakage controls

- Features for a row use **only that player's seasons ≤ the prediction point**;
  targets use season t+1 (and beyond for remaining). Enforced by construction
  and by `test_features_do_not_use_future_seasons` (changing a future season
  leaves earlier rows' features bit-identical).
- **Chronological** split: train on earlier seasons, validate on later ones.
- **Leave-one-player-out (LOPO)**: a player's rows never appear in both train and
  test; baselines are refit inside every fold.
- Predicted seasons are never fed back as training data.

---

## 6. Results — appearances (`y_next_apps`)

| Protocol | naive MAE | age+pos MAE | best model | best MAE | vs naive |
|---|---|---|---|---|---|
| **LOPO** | 6.75 | 6.25 | RandomForest | **5.79** | **−14.2%** |
| **Chronological** (cutoff 2013) | 7.76 | 7.10 | ElasticNet | **6.65** | **−14.3%** |

Both protocols agree: the model beats persistence by ~14% (≈1 appearance less
error per season). This is the strongest result.

**By position (LOPO, RandomForest vs naive MAE):**
| Group | n | naive | model |
|---|---|---|---|
| DEF | 96 | 6.61 | **5.04** (−24%) |
| MID | 142 | 6.51 | **5.63** (−14%) |
| FWD | 65 | 7.85 | **6.32** (−19%) |
| WIDE | 84 | 6.45 | 6.49 (≈naive) |

Defenders and midfielders — the concern in the decision rule — are the **best**
groups, not the worst. Wide players are the only group where the model merely
ties naive.

**By age band (LOPO, apps):** biggest gains at the career ends — `<=21`
7.28→5.15 (−29%) and `34+` 9.15→8.10 (−11%); mid-career (22–25) is already
near-flat (4.44→4.43) because persistence is hard to beat in a player's stable
years.

---

## 7. Results — goals (`y_next_goals`) and goals/appearance

| Protocol | naive MAE | best model | best MAE | vs naive |
|---|---|---|---|---|
| Goals, LOPO | 3.84 | ElasticNet | 3.78 | **−1.6%** |
| Goals, Chronological | 4.31 | ElasticNet | 3.74 | −13% |
| GPA, LOPO | 0.12 | Ridge | 0.12 | −5.5% |

Goals are the **weak spot**. Against an unseen player (LOPO) the model barely
beats "predict last season's goals", and by position it is **worse than naive**
for defenders (1.35→1.46) and wide players (4.63→5.12); it helps only forwards
(8.42→7.53) and midfielders (2.96→2.84). Tier A carries little signal about
*next* season's goals beyond the previous count, because the true drivers
(minutes, shots, xG, role) are Tier B/C and unavailable for free.

---

## 8. Results — continuation / retirement probability

- 14 retirements in 401 rows (rare event). Treated as a **per-season
  probability**, not an age threshold.
- **Logistic (class-balanced):** ROC-AUC **0.918**, Brier 0.069; flags **50%**
  of retirements within its 14 highest-risk seasons (precision@N 0.50).
- **HistGB classifier:** ROC-AUC 0.844, Brier **0.031**, and better calibrated
  (predicted vs observed continuation: 0.79→0.78, 0.91→1.00, 0.998→0.978).

So the two models trade off: logistic ranks retirements better (higher AUC/
recall), HistGB is better calibrated. Both clearly beat the base-rate baseline
(Brier 0.069 balanced / 0.031 HGB vs the constant-rate reference). Calibration
is **reasonable at the high-confidence end**; the rare-event tail is noisy with
only 14 events — a small-sample caveat, not a modelling error.

Remaining-career (experimental, retired only): age+pos MAE 3.03 → best model
**2.60 seasons** (−14%).

---

## 9. Non-negativity & uncertainty

- **All predictions are non-negative**: count outputs are clipped at 0; the
  audited minimum across every model/target after post-processing is **0.0**
  (`non_negativity.all_non_negative = true`). Poisson is inherently ≥0; linear
  models can emit negatives on low-count targets (goals) and are clipped;
  `test_clip_removes_negatives` locks the behaviour in.
- **Uncertainty**: HistGB quantile 10/90 intervals for appearances have a mean
  width of 13.7 and cover **66.7%** of actuals — the nominal-80% interval is
  **under-covered** on this small dataset. Usable as a rough band, but interval
  calibration needs more data.

---

## 10. Example generated career trajectories

`y_next_apps` for **Marco van Basten**, predicted by a HistGB model trained on
the other 19 players (LOPO), vs actual and naive:

| Season | Age | Actual | Model | Naive |
|---|---|---|---|---|
| 1982 | 18 | 26 | 28.1 | 20 |
| 1984 | 20 | 26 | 29.7 | 33 |
| 1986 | 22 | 11 | 29.3 | 27 |
| 1988 | 24 | 26 | 30.1 | 33 |
| 1990 | 26 | 31 | 29.3 | 31 |
| 1991 | 27 | 15 | 29.6 | 31 |
| **1992** | **28** | **0** | **25.7** | **15** |
| 1993 | 29 | 0 | 25.7 | 0 |

The model tracks his peak availability well, but **cannot foresee the
career-ending injury** that dropped him to 0 apps at 28 — it predicts ~26.
Neither does naive. This is the fundamental Tier-A ceiling: injuries and
minutes/fitness are invisible to free data, so sudden collapses are
unpredictable. (Modric and Haaland trajectories in `results.json` show the
opposite, easy case — stable high-availability careers tracked closely.)

---

## 11. Model limitations

1. **Goals are barely predictable** from Tier A beyond persistence, and worse
   than naive for defenders/wingers. The signal that matters (minutes, shots,
   xG, role) is Tier B/C and not freely obtainable.
2. **Injuries/availability shocks are invisible** — the single biggest source of
   large errors (van Basten, van Dijk's ACL year), because minutes/injury data
   is Tier B and unavailable for free.
3. **Position is career-level**, not per-season (Wikipedia gives one primary
   position); role changes over a career are not captured.
4. **Small data** (20 players / 387 rows / 14 retirements): interval calibration
   under-covers and rare-event calibration is noisy.
5. **Cross-era / cross-league mixing**: a 1980s Eredivisie season and a 2020s
   Premier League season are pooled; league strength is not modelled.
6. **Domestic-league scope**: cups and continental games are excluded by design,
   so "appearances" is a partial workload measure.

---

## 12. Decision-rule check

| Rule condition | Result |
|---|---|
| ≥1 model consistently beats naive baselines | **Yes** — appearances: RF −14% LOPO and −14% chronological, positive for DEF/MID/FWD |
| Continuation reasonably calibrated | **Yes (qualified)** — HistGB well-calibrated, AUC 0.84–0.92, probabilistic; rare tail noisy |
| Errors not catastrophically worse for DEF/MID | **Yes** — DEF/MID are the *best* appearance groups; goals slightly worse for DEF but tiny absolute error (~1.4) |
| All generated counts non-negative | **Yes** — audited min 0.0 |
| Reproducible with a fixed seed | **Yes** — seed 42, deterministic (tests confirm) |

All five conditions are met **for appearances, availability, and continuation**.
The one clear shortfall is **goals**, which Tier A cannot predict beyond
persistence.

---

## 13. GO / NO-GO recommendation

**GO (qualified) — proceed with bulk Tier-A collection, but scope the model to
what Tier A can actually predict.**

Rationale: the decision rule's conditions are satisfied by at least one model
(appearances) and hold across positions and both validation protocols; the
data is free, cheap, cached, and reproducible; continuation is a usable
probabilistic signal; and everything is non-negative. Collecting Tier A for the
full roster is worthwhile because it supports a genuinely-better-than-baseline
model for **next-season appearances, availability/workload trend, and
career-continuation probability**, especially for defenders and midfielders and
at the career ends.

**The qualification (equivalent to a NO-GO for the goals objective):** Tier A
**cannot** power a meaningful next-season **goals** model — it barely beats
persistence and is worse than naive for defenders and wingers. If predicting
goals (the production model's current headline output) is the objective, that is
a **NO-GO on Tier A alone**.

**Additional data fields essential to make goals (and robustness) work** — all
Tier B/C, and per the free-source pilot **not** obtainable via free respectful
automation:
- **minutes played** (exposure; the biggest missing denominator),
- **shots / shots on target** and **xG / xA** (finishing signal),
- **injury/availability records** (to anticipate the collapses Tier A can't see),
- ideally **starts** and **per-season position/role**.

Recommended next step before any goals modelling: decide a licensed/manual
source for minutes + shots/xG (from the source acquisition report), or accept an
**appearances-and-continuation-only** model as the free-data product. Do not
begin the 200-player bulk collection until this scope is approved.

---

## 14. Reproduce

```
cd backend/python/model_feasibility
python build_dataset.py     # Tier-A collection via the approved pipeline (cached)
python evaluate.py          # writes results.json (seed 42)
python -m unittest discover -s tests
```
