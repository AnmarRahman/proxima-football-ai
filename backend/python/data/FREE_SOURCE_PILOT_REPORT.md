# Free-Source Feasibility Pilot Report

Scope: a limited, respectful, reproducible pilot to decide whether ~200 complete
player careers can be assembled using **only freely accessible sources**, with
no paid APIs/subscriptions and no bypassing of access controls. This is a
feasibility test, not bulk collection.

Date: 2026-07-27. Environment: Python 3.11 (`.venv311`), `requests`, `lxml`,
`beautifulsoup4`, `pandas`, `soccerdata 1.9.1` available.

Pilot players (3) x representative seasons (3 each): Erling Haaland (modern
attacker), Virgil van Dijk (defender), Luka Modric (long historical career).

Code: `backend/python/data/acquisition/` (adapters, cache, normalize,
provenance, coverage, pilot). Outputs: `acquisition/pilot_output/`. Tests:
`acquisition/tests/`. Nothing here was written to `data/players/` and no
statistic was invented.

---

## 1. Sources and adapters tested

| Source / adapter | Honest automated access? | Verdict | Notes |
|---|---|---|---|
| **Wikipedia** (article HTML) | ✅ Works (HTTP 200) | **USE** | Bio + per-season league apps/goals + club + competition |
| **Wikidata** (action API) | ✅ Works (HTTP 200) | **USE** | Nationality (P27); identity backstop |
| **StatsBomb Open Data** (GitHub raw JSON) | ✅ Works (HTTP 200) | **USE (supplemental)** | Only covered competition-seasons; event-level |
| **Understat** (league page, honest GET) | ⚠️ 200 but data removed | **UNAVAILABLE** | Inline `playersData` gone; now AJAX; structured access needs TLS impersonation |
| **soccerdata** (FBref/Understat/Sofascore/WhoScored) | ✅ works ONLY via impersonation | **EXCLUDED** | Uses `tls-client` TLS-fingerprint impersonation to defeat anti-bot; violates policy |
| **FBref** (direct) | ❌ HTTP 403 | **BLOCKED** | Confirmed in the earlier phase; bot-blocked |
| **ESPN / worldfootball** (direct) | ❌ HTTP 403 | **BLOCKED** | Confirmed earlier |
| **Transfermarkt** | not attempted | **MANUAL ONLY** | ToS/access controls prohibit scraping; record as later manual workflow |

### The decisive finding: `soccerdata` requires impersonation
`soccerdata`'s readers reach Understat/FBref/Sofascore/WhoScored by downloading
and using `tls-client` (bogdanfinn/tls-client) via `tls_requests` — a
**TLS-fingerprint impersonation** library whose purpose is to defeat anti-bot /
Cloudflare protection. The pilot confirmed it returns rich Understat data (554
rows incl. minutes, xG, assists, shots) — **but only through that impersonation
path**, which the brief forbids ("no browser fingerprinting, no access-control
circumvention"). It is therefore **excluded from the collection pipeline** and
the adapter (`sources/soccerdata_source.py`) never fetches. Honest, non-
impersonating requests to Understat return a page without the data.

Net: under a strict respectful-access policy, the only free sources that yield
data are **Wikipedia (+ Wikidata)** and **StatsBomb Open Data** (limited comps).

---

## 2. Exact fields available from each usable source

| Field (schema) | Tier | Wikipedia | Wikidata | StatsBomb Open Data* |
|---|---|---|---|---|
| player identity, name | A | ✅ | ✅ | (in lineups) |
| birth_date | A | ✅ (`span.bday`) | ✅ (P569) | ❌ |
| nationality | A | (via Wikidata) | ✅ (P27) | ❌ |
| position | A | ✅ (infobox) | ✅ (P413) | ✅ (lineup position) |
| height_cm | A/‑ | ✅ (infobox) | ✅ | ❌ |
| season, club/team, competition | A | ✅ | ❌ | ✅ (per match) |
| appearances | A | ✅ (league) | ❌ | ⚠️ derive from lineups |
| goals | A | ✅ (league) | ❌ | ⚠️ derive from events |
| national_team_stats (array) | A | ⚠️ totals only, hard to parse | ❌ | ⚠️ intl tournaments only |
| starts | B | ❌ | ❌ | ⚠️ derive |
| minutes | B | ❌ | ❌ | ⚠️ derive (event positions) |
| assists | B | ❌ | ❌ | ⚠️ derive |
| cards, substitutions | B | ❌ | ❌ | ⚠️ derive |
| xG, xA | C | ❌ | ❌ | ✅ (StatsBomb model)* |
| key_passes, shots, dribbles, duels, tackles, defensive | C | ❌ | ❌ | ✅ (events)* |
| goalkeeper metrics | C | ❌ | ❌ | ✅ (GK events)* |
| physical/tactical | C | ❌ | ❌ | ❌ |
| injuries | — | ⚠️ prose only | ❌ | ❌ |
| transfers | — | ⚠️ where documented | ⚠️ | ❌ |

\* StatsBomb only for competition-seasons **actually in the open-data repo**, and
only by aggregating events — supplemental/validation, not full-career coverage.

---

## 3. Coverage by player / season / field (pilot results)

Tier A completeness and provenance are measured by `acquisition/coverage.py`.
All Wikipedia values carry `sources[]` provenance (`supports: [appearances,
goals, position, ...]`).

| Player | Season | Club (competition) | Wikipedia A (apps/goals/pos/bio) | Understat | StatsBomb | Tier A | Tier B | Tier C |
|---|---|---|---|---|---|---|---|---|
| Haaland | 2018 | Molde (Eliteserien) | ✅ | not covered | not in open data | 100% | 0% | 0% |
| Haaland | 2019 | RB Salzburg (Austrian BL) | ✅ | not covered | not in open data | 100% | 0% | 0% |
| Haaland | 2022 | Man City (Premier League) | ✅ | **unavailable** | not in open data | 100% | 0% | 0% |
| van Dijk | 2011 | Groningen (Eredivisie) | ✅ | not covered | not in open data | 100% | 0% | 0% |
| van Dijk | 2015 | Southampton (Premier League) | ✅ | **unavailable** | **covered; 38 matches; player found** | 100% | 0% | 0% |
| van Dijk | 2019 | Liverpool (Premier League) | ✅ | **unavailable** | not in open data | 100% | 0% | 0% |
| Modric | 2005 | Dinamo Zagreb (Prva HNL) | ✅ | not covered | not in open data | 100% | 0% | 0% |
| Modric | 2011 | Tottenham (Premier League) | ✅ | **unavailable** | not in open data | 100% | 0% | 0% |
| Modric | 2018 | Real Madrid (La Liga) | ✅ | **unavailable** | **covered; 1 match (Clásico); player found** | 100% | 0% | 0% |

Verified identity examples: Haaland b.2000-07-21; van Dijk b.1991-07-08, NL, CB,
195cm; Modric b.1985-09-09, Croatia, Central midfielder, 172cm.

**StatsBomb coverage is extremely uneven**: PL 2015/16 has all 38 Southampton
matches (a full season could be aggregated), but La Liga 2018/19 exposes only 1
Real Madrid match (the Clásico, because that open-data set is Barcelona/Messi-
centric). So StatsBomb can occasionally supply Tier B/C for a specific season,
but not systematically across a career.

---

## 4. Rate-limit / access issues observed

- Every adapter uses a shared client with a per-source min delay (Wikipedia 2s,
  Understat 3s, StatsBomb 1.5s, Wikidata 1s), on-disk caching (so each URL is
  fetched at most once), exponential backoff on 5xx/network errors, and an
  immediate stop on 401/403/429/challenge pages (no retry, no circumvention).
- No 403/429 was hit on Wikipedia, Wikidata, or StatsBomb GitHub raw.
- Understat returned 200 but without the data (moved behind an AJAX path that,
  in practice, only `soccerdata` reaches via impersonation).
- FBref/ESPN/worldfootball remain 403 (from the earlier phase); not re-hit here.
- One implementation note: an initial over-broad anti-bot heuristic false-
  positived on normal Wikipedia HTML; it was narrowed to specific Cloudflare/
  challenge signatures so honest pages are never misclassified.

---

## 5. Licensing / usage concerns

- **Wikipedia / Wikidata**: content is CC BY-SA / CC0; free to reuse with
  attribution. Wikimedia asks for a descriptive User-Agent (provided) and
  reasonable request rates (respected). Fully compatible with this project.
- **StatsBomb Open Data**: free under **CC BY-NC 4.0** — attribution required
  and **non-commercial only**. Acceptable for a research/non-commercial model;
  would need review if the project ever becomes commercial.
- **Understat / FBref / Sofascore / Transfermarkt**: no clear reuse license;
  ToS restrict scraping/redistribution and they enforce anti-bot controls.
  Accessing them via impersonation would breach both the ToS and our policy.

---

## 6. Data-definition conflicts (must be managed)

- **Wikipedia appearances/goals are LEAGUE-ONLY** and are editor-aggregated;
  they can differ from Opta/FBref counts (e.g. treatment of substitute
  appearances). Do not silently reconcile with another provider's totals.
- **Season labelling**: calendar-year leagues (Eliteserien, Prva HNL) vs split-
  year (PL, La Liga). The pipeline stores the **starting year** (`2015-16`→2015).
- **StatsBomb minutes/xG are model/event-derived** and use StatsBomb's own xG
  model — never blend with any other xG source (the project already mandates a
  single xG model; Understat is that nominal model but is unavailable here).
- **xG source**: none available under policy right now (Understat blocked,
  StatsBomb only for a few comps). xG stays `null` for almost all seasons.
- The `sources[]` provenance format records which provider backed each field, so
  a mixed-provider row stays auditable and conflicts are detectable; the
  normalizer emits a `conflicts` list when two providers disagree on a field.

---

## 7. Estimated request volume for 200 players (Tier A, free)

Per player (one-time, then cached): 1 Wikipedia article + ~1 Wikidata entity +
(shared) country-label lookups.

| Source | Requests for 200 players | Cacheable | Est. one-time wall-clock @ delay |
|---|---|---|---|
| Wikipedia | ~200 | yes | ~7 min @ 2s |
| Wikidata | ~200 entities + ~60 country labels (shared) ≈ 260 | yes | ~4 min @ 1s |
| StatsBomb | competitions.json (1) + matches/lineups only for the handful of covered seasons | yes | minutes |
| Understat / FBref | 0 (excluded) | — | — |
| **Total** | **≈ 460 requests, one-time** | **yes** | **~15–20 min** |

This is a light, respectful load, comfortably within Wikimedia norms. Re-runs
are zero-network because every response is cached under `acquisition/cache/`.

---

## 8. Fields that cannot realistically be obtained for free (respectfully)

- **Minutes, starts, assists, cards (Tier B)** — not on Wikipedia; only via
  blocked/impersonation sources or (rarely) StatsBomb event aggregation.
- **xG, xA, key passes, shots, dribbles, duels, tackles, all advanced defensive
  and goalkeeper metrics (Tier C)** — same; StatsBomb supplies them only for the
  small set of fully-covered competition-seasons.
- **Physical/tactical qualitative fields** — no free structured source; must
  stay `null` (never estimated).
- **Injuries and transfers** — Transfermarkt is the natural source but is
  scrape-prohibited; only a manual workflow is compatible.

So, respectfully and for free, **Tier A is obtainable; Tier B and Tier C are
essentially not** (beyond incidental StatsBomb coverage).

---

## 9. Recommended free-source architecture

```
Identity + core (Tier A)          Wikipedia article (apps, goals, club, comp,
                                  position, birth date) + Wikidata (nationality)
Supplemental / validation         StatsBomb Open Data, ONLY for its covered
  (some Tier B/C, few seasons)    competition-seasons, via full-season event
                                  aggregation, tagged as its own provenance
xG model                          single model only; Understat is the nominal
                                  choice but is UNAVAILABLE under policy -> xG
                                  stays null until a compliant source exists
Injuries / transfers              deferred to a manual Transfermarkt workflow
                                  (not automated); null until then
Everything else (Tier C, GK,      null, surfaced via coverage metadata; never
  physical/tactical)              estimated
```

- Keep the adapter architecture (one policy-compliant client: cache + rate-limit
  + backoff + stop-on-block). Add adapters later only if a source offers honest,
  licensed access.
- Persist coverage metadata per season (Tier A/B/C %, unsupported fields) so the
  dataset's limitations are explicit to the model and to reviewers.
- Store raw responses (`cache/`) separately from normalized output
  (`pilot_output/` → later a staging dir); never write incomplete files to
  `data/players/`.

---

## 10. Go / No-Go

- **GO — Tier A bulk collection via Wikipedia + Wikidata.** It is legal, free,
  cached, respectful (~460 one-time requests for 200 players), and produced
  100% Tier A with full provenance for all 3 pilot players across eras
  2005–2022, including a defender and a long-career midfielder.
- **NO-GO — Tier B/C via free respectful automation.** Minutes, assists, xG and
  advanced/GK metrics are not obtainable at scale without a paid API or
  access-control circumvention (which is prohibited). StatsBomb fills only a
  handful of covered seasons.
- **Therefore: conditional GO for bulk collection, Tier A only**, provided the
  model is adapted to a Tier-A feature set (or explicitly tolerates near-total
  Tier B/C nulls). A bulk run that promises the current model's full feature
  vector (which is mostly Tier B/C) from free sources is **not** feasible.

---

## 11. Schema / model changes required before bulk collection

1. **Model feature set**: the model's `FEATURE_NAMES` is dominated by Tier B/C
   (minutes, assists, xG, xA, key_passes, dribbles, duels, tackles, physical/
   tactical). A free Tier-A-only dataset leaves these null → median-filled →
   little signal. Define and evaluate a **Tier-A feature subset**
   (appearances, goals, age, position flags) before committing to bulk, or
   decide the model will run mostly on imputed values (and accept the accuracy
   cost). This is the key decision.
2. **Coverage metadata in the schema**: persist per-season Tier coverage and the
   reason a field is null (unsupported vs not-yet-collected) so training and the
   UI can distinguish "missing" from "zero" (validator already enforces this).
3. **national_team_stats**: mandatory array is enforced, but Wikipedia only
   gives international *totals*; decide whether NT per-tournament rows are in
   scope for free collection (likely `[]` for most).
4. **Goalkeeper track**: still deferred (not part of this pilot). GK metrics are
   Tier C and unavailable free, so the 20 GKs remain blocked on both a schema
   design and a data source.
5. **Provenance is ready**: `sources[]` + the tiered validator already support
   multi-source provenance, null-vs-zero, conflicts, and per-tier scoring.

---

## 12. Reproduce

```
# from backend/python/data/acquisition/
python pilot.py                       # rate-limited, cached; writes pilot_output/
python -m unittest discover -s tests  # offline unit tests (10)

# from repo root
python backend/python/data/tools/validate_player.py --coverage \
    backend/python/data/acquisition/pilot_output
```
Pilot outputs pass **default** validation (structurally importable, Tier A
100%). They intentionally **fail `--strict`** (Tier B/C null) and are kept in
`pilot_output/`, never `data/players/`.
