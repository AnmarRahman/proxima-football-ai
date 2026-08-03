# Schema Compatibility Report — Phase 1

Prepared for the PLAYER_SCRAPE_ROSTER.md collection effort. This documents the
exact schema a player JSON must follow, how every field flows through the
importer into Postgres and then into the model, and the compatibility gaps that
must be resolved before Phase 2 (collecting the remaining 178 players) begins.

Sources of truth for everything below (verified by reading the code, not memory):

- `backend/db/migrations/001_initial_schema.sql` — table columns, types, constraints
- `backend/python/import_players_to_db.py` — how JSON becomes DB rows
- `backend/python/main.py` — the features the model actually reads

Retrieval date: 2026-07-26.

---

## 1. Data flow

```
player JSON file  ->  import_players_to_db.py  ->  Postgres tables  ->  main.py (training/prediction)
                                              \->  main.py also reads the JSON files directly
                                                   (load_all_players_df_from_files)
```

Two independent consumers read the JSON, so a file must satisfy **both**:

1. **Importer / DB** — needs a `player.id`, a numeric `season` per season, and
   type-clean values. Everything else is nullable.
2. **Model** — reads a fixed feature list; unknown / missing values are
   defaulted or median-filled, so the model is tolerant but silent about gaps.

---

## 1a. Validation levels (read this first)

`tools/validate_player.py` reports two tiers, and the two run modes mean
different things:

- **Default validation (`validate_player.py <file>`) = STRUCTURALLY IMPORTABLE.**
  Zero errors means the file will import into Postgres and be read by the model
  without breaking. Warnings are allowed here.
- **Strict validation (`validate_player.py --strict <file>`) = ELIGIBLE FOR THE
  COMPLETED ROSTER.** A player is complete **only when `--strict` reports zero
  errors AND zero warnings.** Any warning (missing sourced stat, a populated
  value without a source, an unknown label, an ongoing season not marked
  partial, …) means the player is not done.

**No file may be copied into `data/players/` until it passes `--strict` with
zero errors and zero warnings.** The Phase-1 example
(`data/examples/virgil-van-dijk.json`) currently **fails `--strict`** because
assists/minutes/advanced stats are unavailable (see §8.2, §9); it therefore
stays in `data/examples/` and must not be promoted.

---

## 2. Two accepted season shapes (both supported)

The importer (`explode_season_rows`) and the model (`extract_competitions`)
accept either shape. All current files except `kylian-mbappe.json` use the flat
shape; mbappe uses the nested shape.

**Flat** (one club-season, stats on the season object):
```json
{ "season": 2019, "team_id": "liverpool", "league_id": "premierleague-2019",
  "position": "Centre-Back", "appearances": 38, "goals": 5, "assists": 7, "minutes": 3420 }
```

**Nested** (season -> teams[] -> competitions[]):
```json
{ "season": 2019,
  "teams": [ { "team_id": "liverpool",
      "competitions": [ { "competition": "Premier League", "appearances": 38, "goals": 5, ... } ] } ] }
```

The DB unique key is `(player_id, season, team_id, league_id)`. In the nested
shape `league_id` is derived from `competition` when not given. A mid-season
transfer is represented as **two rows with the same `season` year** but
different `team_id` — this is legal (distinct unique keys) and is how the
van-dijk example models 2017-18.

> Recommendation: pick **one** shape for Phase 2 and use it for all 178 players
> (rule: "Keep one consistent player ID and team ID format"). The flat shape is
> simpler and is what 20 of 21 existing files use.

---

## 3. Field reference (JSON -> DB -> model)

### player object
| JSON field | DB column (`players`) | Type | Required | Notes |
|---|---|---|---|---|
| `id` | `id` | text PK | **Yes** | importer raises without it; must be a stable slug |
| `name` | `name` | text NOT NULL | Yes | |
| `birth_date` | `birth_date` | date | Recommended | model `age = season - birth_year`; missing -> no age signal |
| `nationality` | `nationality` | text | No | |
| `height_cm` / `weight_kg` | same | int | No | null if unknown |
| `dominant_foot` | `dominant_foot` | text | No | |
| `is_retired` / `retired` / `retired_since` | `is_retired`, `retired_since` | bool/date | Recommended | else status comes from `player_status_overrides.json` |
| `over_35` (optional) | `over_35` | bool | No | else computed: `last_season_year - birth_year >= 35` |

### team object (`teams[]`)
| JSON field | DB column (`teams`) | Notes |
|---|---|---|
| `id` | `id` text PK | lower-cased slug; every `season.team_id` should be declared here |
| `name` | `name` NOT NULL | |
| `country`, `logo_url` | same | optional |

### season object -> `player_seasons`
| JSON field | DB column | DB type | Model feature | Notes |
|---|---|---|---|---|
| `season` | `season` | int NOT NULL | `age` (via birth year) | **null/absent -> season silently dropped by importer** |
| `team_id` | `team_id` | text FK | — | null -> `unknown-team` |
| `league_id` | `league_id` | text | — | part of unique key |
| `appearances` | `appearances` | int | `appearances` | |
| `goals` | `goals` | int | `goals` | |
| `assists` | `assists` | int | `assists` | |
| `minutes` | `minutes` | int | `minutes` | |
| `position` | `position` | text | 8 role flags (§4) | |
| `rating` | `rating` | numeric(4,2) | `rating` | only 4.0–10.0 counted; else nan -> median-filled |
| `xG` / `xg` | `xg` | numeric(8,3) | `xG` | both keys read |
| `xA` / `xa` | `xa` | numeric(8,3) | `xA` | both keys read |
| `key_passes` | `key_passes` | int | `key_passes` | |
| `successful_dribbles` | `successful_dribbles` | int | `successful_dribbles` | |
| `duels_won` | `duels_won` | int | `duels_won` | |
| `shots_per_game` | `shots_per_game` | numeric(6,3) | `shots_per_game` | |
| `tackles_per_game` | `tackles_per_game` | numeric(6,3) | `tackles_per_game` | |
| `fouls_drawn` | `fouls_drawn` | int | `fouls_drawn` | |
| `national_team_stats` | `season_national_stats` (child) | array | — | **mandatory key**; `[]` if none (validator ERROR if absent/non-array) |
| `is_partial` | — (raw_json) | bool | — | must be `true` for ongoing or mid-season-transfer split seasons |
| `sources` | — (raw_json) | array | — | provenance; every populated stat must be in some `supports` (§8.6) |
| `injuries[].days_lost` | `injuries.days_lost` | int | `days_lost` (summed) | record each injury once per season (no cross-competition dupes) |
| `physical_metrics.sprint_speed_kmh` | `sprint_speed_kmh` | numeric(6,3) | `sprint_speed_kmh` | |
| `physical_metrics.{acceleration,stamina,recovery_rate}` | same text | — | mapped to 0–5 (§5) | unknown label -> 0.0 |
| `tactical_data.{contribution_to_build_up,defensive_transitions}` | same text | — | mapped to 0–5 (§5) | unknown label -> 0.0 |
| whole season object | `raw_json` | jsonb | — | full object preserved; **extra keys are safe** |

Child tables: `injuries`, `transfers` (from `transfer_history[]`),
`season_national_stats` (from `national_team_stats[]`). Extra/unknown JSON keys
(e.g. `source_url`, `retrieval_date`, `psychological_factors`,
`external_factors`, `_provenance`) are ignored by both consumers and stored in
`raw_json` — so provenance fields are safe to add.

---

## 4. Position -> model role flags

`position` strings are converted to 8 multi-label flags
(`main.position_features`). A season contributes **no** positional signal if its
label matches none of these. Write labels that hit a rule:

| Role flag | Triggering substrings / tokens |
|---|---|
| `position_goalkeeper` | "goalkeeper", "keeper", `gk` |
| `position_center_back` | "center back", "centre back", `cb`; fallback: "defender" |
| `position_full_back` | "left/right/full/wing back", `lb rb lwb rwb` |
| `position_defensive_midfield` | "defensive/holding midfield", `dm cdm` |
| `position_central_midfield` | "central/centre midfield", `cm`; fallback: "midfield" |
| `position_attacking_midfield` | "attacking midfield", "number 10", `am cam` |
| `position_winger` | "wing", "winger", `lw rw lm rm` |
| `position_striker` | "striker","forward","false 9","second striker","centre forward", `st cf ss` |

Labels are multi-label ("Left Wing / Second Striker" sets winger **and**
striker). Hybrid/number-10 careers should use compound labels. `"Centre-Back"`
(as in the example) correctly maps to `position_center_back` only — verified.

---

## 5. Qualitative label vocabularies (silent-zero risk)

Physical/tactical text labels are mapped to numbers; **anything outside the
vocabulary maps to 0.0 silently.** Use only these (case-insensitive):

- **physical_metrics** (acceleration, stamina, recovery_rate): poor, low,
  medium, moderate, high, very high, very fast, good, improving, developing,
  normal, fast, excellent, elite
- **tactical_data** (contribution_to_build_up, defensive_transitions): low,
  limited, below average, medium, moderate, high, very high, world class

> Finding: existing files frequently use out-of-vocabulary labels such as
> "Strong", "Rising", "Powerful", "Fast"(for tactical), "Solid", "Elite"(ok).
> Every out-of-vocab label is currently contributing **0.0**. The validator
> flags these. Standardize labels in Phase 2, or extend the mappings in
> `main.py`.

---

## 6. Numeric sanity ranges (model clamps)

Values outside these still import but the model clamps them; the validator warns
(`main.NUMERIC_CLAMPS`): appearances 0–80, goals 0–100, assists 0–60, minutes
0–7000, rating 4–10, xG 0–80, xA 0–50, key_passes 0–250, successful_dribbles
0–400, duels_won 0–600, shots_per_game 0–10, tackles_per_game 0–8, fouls_drawn
0–200, days_lost 0–365, sprint_speed_kmh 20–45.

---

## 7. Quality gates -> validator mapping

`tools/validate_player.py` encodes the roster's "Dataset Quality Gates" in the
two tiers described in §1a.

**ERROR — default validation (structurally invalid / import-breaking / hard
contract requirement):**
- non-object root, missing `player`/`teams`/`seasons`, missing `player.id`,
  missing/non-numeric `season`, `teams`/`injuries`/`national_team_stats` not a
  list, empty `seasons`, malformed nested `competitions`;
- **`national_team_stats` absent from a season** (mandatory: must be present as
  an array, `[]` if none);
- `season.team_id` not declared in `teams[]`;
- **duplicate `(season, team_id, league_id)`** (the unique-constraint gate);
- **aggregate / "all competitions" row present alongside individual competition
  rows** for the same team-season (double-counting);
- **the same injury duplicated across competition rows** in one season
  (`days_lost` is summed by the model → double-counting);
- **youth club / youth competition** season row (senior careers only);
- `is_partial` present but not a boolean.

**warning — strict-only (completeness / quality / provenance; each one blocks
"complete"):**
- missing sourced `appearances/goals/assists/minutes/position/team_id`, missing
  `league_id`;
- a **populated statistic not covered by any `sources[].supports`** entry
  (every sourced value, including a sourced `0`, needs a source);
- malformed / incomplete `sources[]` entry (missing `provider`/`url`/
  `retrieved_at`/`supports`), or legacy `source_url` used without migration;
- national-team entry populated without provenance; **youth national-team
  record** present;
- an **ongoing season (current) or a split (mid-season-transfer) season not
  marked `is_partial: true`**;
- out-of-range numbers, non-whole integers, unknown qualitative labels, position
  that maps to no role, goalkeeper in the outfield schema, `appearances>0` with
  `minutes==0` (invented-zero smell), pre-2000 seasons.

`null` vs sourced `0`: the validator treats `null` as *missing* (a completeness
warning) and a numeric `0` as *populated* (it must be covered by a source). This
keeps "unknown" and "sourced zero" distinguishable, as required.

Run it:
```
python data/tools/validate_player.py data/players                 # whole dir
python data/tools/validate_player.py --strict data/examples/virgil-van-dijk.json
```
Current results: 20 of 21 existing files pass **default** validation;
`kylian-mbappe.json` now **fails default** because its nested seasons omit the
newly-mandatory `national_team_stats` array (10 errors) — it must be fixed
before it is trustworthy. The Phase-1 example passes default (0 errors) and
**fails `--strict`** (38 warnings) on the unsourced assists/minutes and the two
unsourced split-season rows — expected and documented in §9. None of the
existing files pass `--strict` yet (all carry provenance/label warnings), so
none are "complete" under the tightened contract.

---

## 8. Compatibility findings & gaps (must resolve before Phase 2)

### 8.1 Goalkeepers have no schema and no target (BLOCKER for the 20 GKs)
The roster wants a **separate** goalkeeper model needing saves, save %,
post-shot xG, clean sheets, crosses stopped, sweeping actions, and goals
conceded. **None of these exist** in `player_seasons` or in the model's
`FEATURE_NAMES`, and the model's target is goals/assists-centric. Collecting
the 20 GKs against the current schema would lose all goalkeeping signal.
**Action:** design a GK schema extension + GK feature/target set (and likely a
separate table or `raw_json` convention) before collecting goalkeepers.

### 8.2 Sourcing feasibility for assists / minutes / xG (BLOCKER for the gate)
The gate requires **sourced** appearances, goals, assists, and minutes. During
Phase 1, automated fetching was tested:
- **FBref, worldfootball.net, ESPN** all return **HTTP 403** to `WebFetch`
  (bot-blocked). ESPN was reachable via search but its parsed table was garbled
  (misreported starts) and carries **no minutes** column.
- **Wikipedia** is fetchable and reliable but its career table has **only
  appearances and goals** (no assists, no minutes, no xG).

So the fields that distinguish this dataset (assists, minutes, xG/xA, advanced
stats) currently have **no automated, trustworthy source path**. **Action:**
choose an acquisition method before Phase 2 — e.g. FBref CSV/Stathead export,
the StatsBomb open-data repo (already in Reference Pools; GitHub raw is
fetchable), a licensed API, or a manual/download workflow. This decision gates
the whole roster.

### 8.3 Existing corpus is estimated and attacker-only
The 21 current files are all wingers/strikers/hybrids and carry **no per-season
provenance**; their physical/tactical labels are largely out-of-vocabulary
(→ 0.0, §5) and their advanced fields appear estimated, not sourced. This both
skews the model ("trained only on superstars will overpredict everyone") and
violates the provenance rule. This project does **not** permit estimated data;
Phase 2 must source these fields or leave them `null` (never estimate). Note
that under the tightened contract **none of the 21 files pass `--strict`**, and
`kylian-mbappe.json` fails **default** (missing `national_team_stats`).

### 8.4 null vs sourced-zero
In the **DB**, null stays null (correct). In the **model's** flat features,
`safe_float(null)=0.0`, so a null reads as 0 for that feature (rating is the
exception — nan, then median-filled). The **validator** keeps the two distinct:
`null` = missing (completeness warning); a numeric `0` = populated (must be
covered by a `sources[]` entry). Use `null` only when genuinely unavailable,
never as an invented zero; record a `0` only when the source actually says 0.

### 8.5 Silent season loss
If `season` is null/absent, `explode_season_rows` returns `[]` and the season is
dropped with no error. The validator makes this a hard ERROR.

### 8.6 Provenance format
The contract's full source format is supported:
```json
"sources": [
  { "provider": "FBref", "url": "https://...", "retrieved_at": "YYYY-MM-DD",
    "supports": ["appearances", "goals", "assists", "minutes"] }
]
```
Every populated statistic must appear in some entry's `supports`. `sources` may
sit on a season (flat) or a competition (nested) or be inherited from the season
object. Legacy per-season `source_url` + `retrieval_date` is still accepted for
backward compatibility, but the validator warns to migrate to `sources[]`.

---

## 9. Phase-1 example: `data/examples/virgil-van-dijk.json` (INCOMPLETE)

A centre-back (fills the attacker-only gap) chosen for a long, well-documented,
injury-affected career (2010–2025, incl. the 2020 ACL rupture and the 2018
mid-season transfer). It is an **incomplete structural example only** — it is
**not** eligible for collection and **must not be copied into `data/players/`**.

- **Sourced from Wikipedia** (`sources[]`, provider=Wikipedia,
  retrieved_at=2026-07-26, supports=["appearances","goals"]): appearances,
  goals, club, competition, position, biography, transfers, the ACL injury dates.
- **Left null (not invented):** assists, minutes, xG/xA, rating, and all
  physical/tactical fields — no trustworthy automated source was reachable (§8.2).
- Mandatory `national_team_stats: []` on every season; the two 2017-18 split
  rows are marked `is_partial: true` with null appearances/goals (the per-club
  split is not sourced).

Verification performed:
- `validate_player.py` (default) → **0 errors** → structurally importable.
- `validate_player.py --strict` → **FAILS (0 errors, 38 warnings)** → **not
  eligible for the completed roster.** This failure is expected: the source data
  for assists/minutes/advanced stats is unavailable (§8.2). The file is labelled
  incomplete in its `_status` field.
- Ran the real `main.flatten_season` / `position_features` over all 17 rows:
  every row maps to `position_center_back=1.0`, ages compute 19→34, sourced
  apps/goals flow through, feature width = 29 (21 stats + 8 roles). Model-ready
  in structure, incomplete in data.

---

## 10. Phase-2 readiness checklist

- [ ] Decide the core-stats + advanced-stats acquisition sources
      (see `SOURCE_ACQUISITION_REPORT.md`, §8.2) — **blocks start**
- [ ] Design goalkeeper schema + GK model target (§8.1) — **blocks the 20 GKs**
- [ ] Pick one season shape (flat recommended) and one ID convention
- [ ] Standardize physical/tactical labels to the vocabulary in §5
- [ ] Use the `sources[]` provenance format (already in the template)
- [ ] Fix `kylian-mbappe.json` (add `national_team_stats`) and backfill
      provenance on the other 20 existing files
- [ ] Gate every new file through `validate_player.py --strict` (zero errors AND
      zero warnings) before copying it into `data/players/` and marking it
      complete in PLAYER_SCRAPE_ROSTER.md
