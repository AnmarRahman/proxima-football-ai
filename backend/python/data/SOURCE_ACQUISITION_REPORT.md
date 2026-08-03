# Source Acquisition Report

Goal: choose how to acquire **complete senior career data for ~200 players**
(≈180 outfield + 20 goalkeepers, per `PLAYER_SCRAPE_ROSTER.md`), with the
sourced fields the schema and gates require: appearances, **starts**, goals,
assists, **minutes**, xG/xA, defensive metrics, goalkeeper metrics, plus
injuries and transfers — each with per-statistic provenance.

Prepared: 2026-07-26. **Caveat:** provider pricing, rate limits, coverage
depth, and terms of service change frequently and differ by plan/region. Treat
every number below as "verify before committing." Coverage claims for StatsBomb
Open Data were checked directly against its repo; other providers are assessed
from their documented offerings and must be re-confirmed against a current quote
and a read of the live ToS before any automated collection.

Legend for coverage: ✅ good / ⚠️ partial or conditional / ❌ not available.

---

## 0. What "complete career" requires

For each player we need **every senior club season** (and optionally national
team), one row per season per competition, with consistent metric definitions
across a 15–25 year span. That immediately rules out any single free source:
free datasets are either competition-scoped (StatsBomb) or metric-shallow
(Wikipedia = apps+goals only, confirmed in the compatibility report). The
realistic answer is **1 paid/authoritative core provider + 1 injuries/transfers
provider**, with free sources used only for validation.

---

## 1. Option comparison (summary table)

| Provider | Comps / seasons | Apps | Starts | Goals | Assists | Minutes | xG/xA | Defensive | GK metrics | Injuries | Transfers | Historical depth | Automation | Licensing | Approx cost | Fit for 200 careers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **FBref** (Opta/StatsPerform data) | Very broad (100+ comps) | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ 2017-18+ | ✅ | ✅ (adv GK) | ❌ | ⚠️ basic | ✅ apps/goals decades; advanced ~2017+ | ❌ scraping blocked (403/429, Cloudflare) | ⚠️ personal use; bulk scrape against ToS | Free site / Stathead sub | ⚠️ best data, hard to automate legally |
| **Stathead** (Sports Ref paid) | Same as FBref | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ 2017-18+ | ✅ | ✅ | ❌ | ⚠️ | ✅ | ⚠️ query + CSV export, not a bulk API | ✅ subscriber use; **no redistribution** | ~$8/mo, ~$80/yr | ⚠️ legit export, still semi-manual |
| **Manual FBref CSV export** | Same as FBref | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ 2017-18+ | ✅ | ✅ | ❌ | ⚠️ | ✅ | ❌ manual only | ⚠️ personal use | Free | ⚠️ accurate but very labor-intensive |
| **API-Football** (api-sports.io) | 1,100+ leagues/cups | ✅ | ✅ (lineups) | ✅ | ✅ | ✅ | ⚠️ limited/partial | ⚠️ some (tackles, duels, dribbles) | ⚠️ saves, conceded (no PSxG) | ✅ endpoint (recent) | ✅ endpoint | ⚠️ major leagues ~2010+, uneven older | ✅ REST API | ✅ commercial per plan | Free 100 req/day; ~$25–$150+/mo | ✅ automatable core; advanced/GK shallow |
| **Sportmonks** (Football API) | Broad (plan-gated bundles) | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ add-on | ⚠️ via events/stats | ⚠️ basic | ✅ | ✅ | ⚠️ recent strong, older varies | ✅ REST API | ✅ commercial per plan | ~€39/mo Euro plan; more for xG/worldwide | ✅ automatable; cost scales with breadth |
| **StatsBomb Open Data** | 24 comps, selected seasons (verified) | ⚠️ derive from events | ⚠️ lineups | ✅ (events) | ⚠️ derive | ✅ (events) | ✅ (their model) | ✅ rich events | ✅ rich GK events | ❌ | ❌ | ⚠️ marquee comps only | ✅ GitHub raw | ✅ free, CC BY-NC (attribution, **non-commercial**) | Free | ❌ not career data; validation only |
| **Understat** | Top-5 EU leagues + RPL, 2014/15+ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ (their model) | ❌ | ❌ | ❌ | ❌ | ⚠️ 2014+ only, 6 leagues | ⚠️ page-embedded JSON, no official API | ⚠️ unofficial | Free | ⚠️ good free modern xG, narrow scope |
| **Transfermarkt** | Global clubs | ✅ | ⚠️ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ **best** (injury history, days/games missed) | ✅ **best** (fees, dates) | ✅ deep | ❌ scraping against ToS, bot-blocked | ❌ ToS prohibits scraping/redistribution | Free site | ⚠️ best injuries/transfers, not legally automatable |
| **Official league sites** (PL, LaLiga, Bundesliga, UEFA/FIFA) | Own competition only | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ some | ⚠️ some | ⚠️ some | ❌ | ❌ | ⚠️ own comp era | ⚠️ mostly no open API | ❌ generally not licensed for reuse | Free/NA | ❌ fragmentary across a multi-league career |
| **Enterprise: Opta/Stats Perform, Wyscout, Sportradar** | Everything | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ deep | ✅ licensed feeds | ✅ full commercial | $$$$ (thousands+/yr, contract) | ✅ gold standard if budget allows |

---

## 2. Per-option detail

### 2.1 StatsBomb Open Data (verified against the repo)
`data/competitions.json` lists **24 competitions**, each only for **selected
seasons**, e.g. La Liga (many seasons — largely the Messi/Barcelona archive),
Champions League finals back to the 1970s, FIFA World Cups (1958–2022), Euros
(2020, 2024), plus women's competitions; Premier League only **2003/04 &
2015/16**, Serie A only **2015/16 & 1986/87**, Bundesliga only **2015/16 &
2023/24**. It is **event-level** (aggregate to season yourself), has **no
injuries or transfers**, and is **CC BY-NC (non-commercial + attribution)**.
**Conclusion:** it does **not** provide complete player careers and cannot be
the backbone. It is excellent for **validation and feature engineering** on the
specific covered competitions, and for rich GK/defensive event features where a
player's season is covered.

### 2.2 FBref (Sports Reference; underlying data from Opta/Stats Perform)
The most complete **free** career view: per-season, per-competition apps,
starts, minutes, goals, assists, and — from ~2017-18 for Opta-covered leagues —
xG, xA, npxG, SCA/GCA, progressive carries/passes, plus a full defensive suite
(tackles, interceptions, blocks, clearances) and **advanced goalkeeping**
(PSxG, PSxG+/−, save%, launch%, sweeper actions, cross-stopping). Basic
apps/goals go back decades; advanced metrics are modern-only. **Automation is
the problem:** FBref is behind bot protection and returns **403/429** to
programmatic fetches (confirmed in Phase 1). Its ToS/robots restrict bulk
scraping. Legitimate routes are **manual CSV export** (each table has
"Get table as CSV") or a **Stathead** subscription.

### 2.3 Stathead / manual FBref CSV
**Stathead** (~$8/mo, ~$80/yr) is Sports Reference's paid query tool; it allows
filtered queries and CSV export of the same data, for **subscriber use only —
redistribution is not permitted**. It is not a bulk REST API, so collecting 200
careers is still a guided, semi-manual effort (many queries/exports). **Manual
FBref export** is free but even more labor-intensive. Both give the best metric
breadth and historical depth with a single consistent (Opta) definition set.

### 2.4 API-Football (api-sports.io)
A true REST API covering 1,100+ leagues. Endpoints: `players` (season
statistics: appearances, lineups=starts, minutes, goals, assists, plus shots,
passes, tackles, duels, dribbles), `injuries`, `transfers`, `fixtures`. **xG is
limited/partial** and **advanced defensive/GK depth is shallow** (saves and
goals conceded, no PSxG). Historical player stats are solid for major leagues
from roughly 2010 but thin/uneven before that. **Free tier 100 req/day**; paid
tiers roughly **$25–$150+/mo** (RapidAPI or direct) scaling daily request
volume. Automation is explicitly allowed; commercial use is licensed per plan.
Best **automatable core** for apps/starts/goals/assists/minutes + injuries +
transfers, but not for advanced/GK metrics.

### 2.5 Sportmonks
Subscription REST API with strong recent coverage, detailed events, lineups,
minutes, **injuries/suspensions**, **transfers**, and xG as a paid add-on.
Pricing is bundle-based (e.g. ~€39/mo European plan; worldwide + xG/advanced
costs more). Automation allowed, commercial per plan. Comparable role to
API-Football; choice between them comes down to a coverage/price test on the
specific leagues in this roster.

### 2.6 Understat
Free **xG/xA** and shot data for the **top-5 European leagues + Russian PL**,
**2014/15 onward** only. Per player season: games, minutes, goals, assists, xG,
xA, npxG, shots, key passes. No starts, no defensive metrics, no GK, no
injuries/transfers. No official API (data is embedded as JSON in the page).
Useful **free modern-xG supplement** for seasons within its narrow scope.

### 2.7 Transfermarkt
The best source for **injuries** (full injury history with dates and
games/days missed) and **transfers** (fees, dates, loan/permanent), plus
apps/goals/assists/minutes and market values, with deep history. **But**:
unofficial, ToS **prohibits scraping/redistribution**, and it is bot-blocked
(403 in Phase 1). Realistically usable only manually or via a licensed
reseller — treat as a manual reference for injuries/transfers, not an
automatable feed.

### 2.8 Official league / competition sources
Premier League, LaLiga, Bundesliga, UEFA, FIFA each publish stats for **their
own competition only**, mostly without an open, licensed API. A single career
spans many competitions, so this route means stitching together many
inconsistent sources with restrictive terms — impractical for 200 multi-league
careers. Useful only as an official cross-check for a specific current
competition (as the roster's UEFA squad-list note suggests).

### 2.9 Enterprise feeds (Opta/Stats Perform, Wyscout, Sportradar)
Fully licensed, most complete on every axis including defensive and GK metrics
and deep history, delivered as proper feeds. Cost is enterprise-scale
(thousands+/year, negotiated contracts). The gold standard **if budget allows**;
likely overkill for a ~200-player research dataset.

---

## 3. Recommendations

### 3.1 Best source for core historical statistics
**FBref (via a Stathead subscription for legitimate export).** It uniquely
combines deep history (apps/starts/minutes/goals/assists back decades), a full
defensive suite, advanced GK tables, and one consistent Opta definition set.
The trade-off is that collection is semi-manual (query + CSV export), not a bulk
API. **If automation is mandatory**, use **API-Football** as the core instead
and accept shallower advanced/GK coverage, supplementing depth from FBref.

### 3.2 Best source for modern advanced statistics (xG/xA, progressive, defensive)
**FBref/Opta** for breadth and defensive + GK advanced metrics (2017-18+).
**Understat** is a solid **free** fallback for xG/xA, but only for the top-5
leagues from 2014/15 — and its xG model differs from Opta's (see §4). For an
API path, **Sportmonks' xG add-on** (or API-Football where available).

### 3.3 Best source for injuries and transfers
**Transfermarkt** has the deepest, cleanest injury and transfer history — but
its ToS forbids scraping, so use it **manually** or via a licensed reseller.
For an **automatable** alternative, **API-Football** (or Sportmonks) `injuries`
and `transfers` endpoints, accepting less historical depth on older injuries.

### 3.4 Can multiple providers be combined without incompatible definitions?
**Yes for disjoint metric families; no for the same metric from two models.**
Safe pattern:
- **One** provider for the counting/core stats and advanced metrics
  (apps, starts, minutes, goals, assists, xG, defensive, GK) so definitions are
  internally consistent.
- **One** provider for injuries and transfers (a different family; no overlap).
- **Never blend two xG sources** — StatsBomb, Opta (FBref), and Understat each
  use a different xG model; mixing them corrupts the feature. Pick one xG model
  for the whole dataset.
- Watch definition mismatches even for "simple" stats: **appearances** and
  **minutes** differ between providers (e.g. how substitute cameos, added time,
  and competition scope are counted). Reconcile to one definition and record
  which source backed each value.

The project's `sources[]` provenance format already supports this:
`supports` declares exactly which fields each source backed, so a mixed-provider
file stays traceable and the validator confirms every populated stat has a
matching source. **Rule:** never let one competition-season row mix two
providers for the *same* metric.

---

## 4. Definition-compatibility watch-list

- **xG models are not interchangeable** (StatsBomb ≠ Opta ≠ Understat).
- **Appearances**: starts-only vs starts+sub cameos; total vs domestic-league.
- **Minutes**: some sources exclude stoppage time; some estimate.
- **Assists**: Opta "assist" vs broader "key pass leading to goal" definitions.
- **Season labelling**: calendar-year leagues (e.g. MLS, Nordic, Argentina)
  vs split-year (`2015-16` → store starting year `2015`, per the schema).
- **Competition granularity**: keep per-competition rows; never import an
  "all competitions" aggregate alongside them (the validator errors on this).

---

## 5. Suggested path for this project (~200 careers, research/non-commercial)

1. **Pilot (no cost):** confirm exact league/season/metric coverage for ~5
   roster players on a **free API-Football tier** and on **FBref/Stathead**;
   measure how many required fields each fills per season.
2. **Core provider decision:** if legitimate automation is required, adopt
   **API-Football or Sportmonks** as the automatable core (apps/starts/minutes/
   goals/assists + injuries + transfers). If manual effort is acceptable and
   maximum accuracy/history matters, adopt **FBref via Stathead**.
3. **Advanced/GK layer:** fill xG/xA, defensive, and goalkeeper metrics from
   **FBref/Opta** (one model), or Understat for free modern xG within scope —
   but only after the goalkeeper schema is designed (that work is deferred).
4. **Injuries/transfers:** Transfermarkt manually, or the core API's endpoints
   for automation.
5. Record every value's origin via the `sources[]` format and gate every file
   with `validate_player.py --strict` (zero errors and zero warnings) before it
   enters `data/players/`.

**Blocking decisions before Phase 2:** (a) pick the core provider and confirm
its coverage/terms/budget; (b) confirm an injuries/transfers source; (c) decide
the single xG model. None of these should be assumed — each needs a current
quote and a live ToS read.
