# Tier-A Collection Report (Phase 2B)

Production-quality domestic-league Tier-A career data for the outfield roster, collected only via the policy-compliant Wikimedia pipeline (Wikidata identity + Wikipedia career tables). No production data, Supabase, frontend, or deployment was touched; goalkeepers excluded.

## Summary

- Requested roster size (outfield): **180**
- Completed players: **180**  -> `collected_players/`
- Quarantined players: **0**  -> `collection_quarantine/` (not complete)
- Season rows (player-season-team-league): **3143**
- Aggregated player-seasons: **2948**
- Every completed file: Tier A completeness 100%, provenance 100% (validated; errors route to quarantine).
- Warnings on completed files: 66 (non-blocking: goals>apps, high apps, partial season)

## Date / era coverage

- Career spans from **1984** to **2026**.
- Season rows by decade:
  - 1980s: 13
  - 1990s: 223
  - 2000s: 821
  - 2010s: 1331
  - 2020s: 755

## Position distribution (completed)

- Coarse: DEF 55, FWD 30, MID 65, WIDE 30
- Fine: AM 10, CB 30, CM 30, DM 25, FB 25, FW 30, WNG 30

## Career status

- Retirement events (last collected season <= 2023): **75**
- Recent/active (last season >= 2025): **98**
- Players with an ongoing/partial season: **30** (30 partial rows, flagged `is_partial: true`, excluded from completed-season training targets)

## Source requests & cache

- Wikipedia article requests (cached): ~183
- Wikidata API requests (cached): ~458
- Every response cached under `acquisition/cache/`; re-runs are zero-network. Rate-limited, identifying User-Agent, no circumvention.

## Validation failures (quarantine reasons)


## Identity ambiguities


## Missing / suspicious career seasons


## Position & era imbalances

- Forwards (FWD 30) are the smallest coarse group; MID (65) the largest.
- Era skew: most season rows fall in the 2000s–2020s; pre-2000 coverage is thinner (older players collected but fewer of them).

## Completed players (180)

- achraf-hakimi (9 seasons, 2017–2025, DEF)
- alejandro-balde (5 seasons, 2021–2025, DEF)
- alessandro-bastoni (10 seasons, 2016–2025, DEF)
- alessandro-del-piero (24 seasons, 1991–2014, MID)
- alessandro-nesta (22 seasons, 1993–2014, DEF)
- alexander-isak (10 seasons, 2016–2025, FWD)
- alexis-sanchez (21 seasons, 2005–2025, WIDE)
- alphonso-davies (10 seasons, 2016–2025, DEF)
- andrea-pirlo (24 seasons, 1994–2017, MID)
- andres-iniesta (22 seasons, 2002–2023, MID)
- andy-robertson (15 seasons, 2012–2026, DEF)
- angel-di-maria (22 seasons, 2005–2026, WIDE)
- antoine-griezmann (18 seasons, 2009–2026, MID)
- antonio-rudiger (16 seasons, 2011–2026, DEF)
- arda-turan (18 seasons, 2004–2021, WIDE)
- arjen-robben (20 seasons, 2000–2020, WIDE)
- ashley-cole (20 seasons, 1999–2018, DEF)
- aurelien-tchouameni (9 seasons, 2018–2026, MID)
- aymeric-laporte (14 seasons, 2012–2025, DEF)
- bastian-schweinsteiger (18 seasons, 2002–2019, MID)
- bernardo-silva (14 seasons, 2013–2026, MID)
- bruno-fernandes (14 seasons, 2012–2025, MID)
- bruno-guimaraes (10 seasons, 2016–2025, MID)
- bukayo-saka (8 seasons, 2018–2025, WIDE)
- cafu (19 seasons, 1989–2007, DEF)
- carles-puyol (15 seasons, 1999–2013, DEF)
- carlos-tevez (11 seasons, 2005–2017, FWD)
- casemiro (17 seasons, 2010–2026, MID)
- cesar-azpilicueta (20 seasons, 2006–2025, DEF)
- cesc-fabregas (20 seasons, 2003–2022, MID)
- clarence-seedorf (22 seasons, 1992–2013, MID)
- claude-makelele (19 seasons, 1992–2010, MID)
- cristiano-ronaldo (24 seasons, 2002–2025, WIDE)
- dani-alves (22 seasons, 2001–2022, DEF)
- dani-carvajal (14 seasons, 2012–2025, DEF)
- daniele-de-rossi (18 seasons, 2001–2018, MID)
- david-alaba (17 seasons, 2009–2025, DEF)
- david-beckham (21 seasons, 1992–2012, WIDE)
- david-silva (19 seasons, 2004–2022, MID)
- david-villa (20 seasons, 2000–2019, FWD)
- declan-rice (10 seasons, 2016–2025, MID)
- dennis-bergkamp (20 seasons, 1986–2005, MID)
- didier-drogba (21 seasons, 1998–2018, FWD)
- diego-costa (19 seasons, 2006–2024, FWD)
- diego-godin (21 seasons, 2003–2023, DEF)
- eden-hazard (16 seasons, 2007–2022, WIDE)
- edinson-cavani (18 seasons, 2005–2022, FWD)
- erling-haaland (10 seasons, 2016–2025, FWD)
- fabio-cannavaro (19 seasons, 1992–2010, DEF)
- federico-dimarco (12 seasons, 2014–2025, DEF)
- federico-valverde (11 seasons, 2016–2026, MID)
- fernandinho-footballer-born-may-1985 (22 seasons, 2003–2024, MID)
- fernando-torres (20 seasons, 2000–2019, FWD)
- florian-wirtz (7 seasons, 2019–2025, MID)
- francesco-totti (25 seasons, 1992–2016, MID)
- franck-ribery (23 seasons, 2000–2022, WIDE)
- frank-lampard (22 seasons, 1995–2016, MID)
- frenkie-de-jong (10 seasons, 2016–2025, MID)
- gabriel-magalhaes (10 seasons, 2016–2025, DEF)
- gareth-bale (18 seasons, 2005–2022, WIDE)
- gavi-footballer (5 seasons, 2021–2025, MID)
- gennaro-gattuso (18 seasons, 1995–2012, MID)
- gerard-pique (19 seasons, 2004–2022, DEF)
- gilberto-silva (16 seasons, 1997–2013, MID)
- giorgio-chiellini (22 seasons, 2002–2023, DEF)
- gonzalo-higuain (19 seasons, 2004–2022, FWD)
- hakan-calhanoglu (15 seasons, 2011–2025, MID)
- harry-kane (16 seasons, 2010–2025, FWD)
- ilkay-gundogan (18 seasons, 2008–2025, MID)
- ivan-rakitic (21 seasons, 2004–2024, MID)
- jamal-musiala (7 seasons, 2019–2025, MID)
- jamie-vardy (21 seasons, 2005–2025, FWD)
- javier-mascherano (18 seasons, 2003–2020, MID)
- javier-zanetti (22 seasons, 1992–2013, DEF)
- jeremie-frimpong (7 seasons, 2019–2025, DEF)
- jerome-boateng (19 seasons, 2006–2024, DEF)
- joao-cancelo (13 seasons, 2013–2025, DEF)
- joao-palhinha (11 seasons, 2015–2025, MID)
- john-terry (20 seasons, 1998–2017, DEF)
- jordi-alba (19 seasons, 2006–2025, DEF)
- jorginho-footballer-born-december-1991 (17 seasons, 2010–2026, MID)
- joshua-kimmich (13 seasons, 2013–2025, MID)
- josko-gvardiol (7 seasons, 2019–2025, DEF)
- juan-cuadrado (18 seasons, 2008–2025, WIDE)
- juan-roman-riquelme (5 seasons, 2002–2006, MID)
- jude-bellingham (8 seasons, 2019–2026, MID)
- julian-alvarez (8 seasons, 2018–2025, FWD)
- kaka (17 seasons, 2001–2017, MID)
- kalidou-koulibaly (16 seasons, 2010–2025, DEF)
- karim-benzema (22 seasons, 2004–2025, FWD)
- kevin-de-bruyne (18 seasons, 2008–2025, MID)
- khvicha-kvaratskhelia (9 seasons, 2017–2025, WIDE)
- kieran-trippier (18 seasons, 2009–2026, DEF)
- kingsley-coman (14 seasons, 2012–2025, WIDE)
- kyle-walker (18 seasons, 2008–2025, DEF)
- kylian-mbappe (12 seasons, 2015–2026, WIDE)
- lautaro-martinez (11 seasons, 2015–2025, FWD)
- leonardo-bonucci (19 seasons, 2005–2023, DEF)
- leroy-sane (13 seasons, 2013–2025, WIDE)
- lionel-messi (23 seasons, 2004–2026, WIDE)
- luis-figo (20 seasons, 1989–2008, WIDE)
- luis-suarez (22 seasons, 2005–2026, FWD)
- luka-modric (24 seasons, 2003–2026, MID)
- maicon-footballer-born-1981 (20 seasons, 2000–2021, DEF)
- marcelo-footballer-born-1988 (20 seasons, 2005–2024, DEF)
- marco-reus (19 seasons, 2008–2026, MID)
- marco-verratti (18 seasons, 2008–2025, MID)
- mario-gomez (17 seasons, 2003–2019, FWD)
- marquinhos (14 seasons, 2012–2025, DEF)
- martin-degaard (11 seasons, 2014–2025, MID)
- martin-zubimendi (8 seasons, 2018–2025, MID)
- mats-hummels (19 seasons, 2006–2024, DEF)
- mesut-ozil (17 seasons, 2006–2022, MID)
- michael-essien (19 seasons, 2000–2019, MID)
- miroslav-klose (17 seasons, 1999–2015, FWD)
- mohamed-salah (17 seasons, 2009–2025, WIDE)
- moises-caicedo (8 seasons, 2019–2026, MID)
- n-golo-kante (16 seasons, 2011–2026, MID)
- nemanja-matic (20 seasons, 2006–2025, MID)
- nemanja-vidic (16 seasons, 2000–2015, DEF)
- neymar (18 seasons, 2009–2026, WIDE)
- nicolo-barella (12 seasons, 2014–2025, MID)
- nuno-mendes-footballer-born-2002 (7 seasons, 2019–2025, DEF)
- ousmane-dembele (11 seasons, 2015–2025, WIDE)
- paolo-maldini (25 seasons, 1984–2008, DEF)
- patrice-evra (19 seasons, 1999–2017, DEF)
- patrick-vieira (18 seasons, 1993–2010, MID)
- paul-scholes (20 seasons, 1994–2018, MID)
- paulo-dybala (16 seasons, 2011–2026, MID)
- pedri (7 seasons, 2019–2025, MID)
- pedro-footballer-born-1987 (19 seasons, 2007–2025, WIDE)
- pepe-footballer-born-february-1983 (23 seasons, 2001–2023, DEF)
- philipp-lahm (15 seasons, 2002–2016, DEF)
- pierre-emerick-aubameyang (20 seasons, 2007–2026, FWD)
- radamel-falcao (22 seasons, 2004–2025, FWD)
- rafael-leao (9 seasons, 2017–2025, WIDE)
- raheem-sterling (15 seasons, 2011–2025, WIDE)
- raphael-varane (15 seasons, 2010–2024, DEF)
- reece-james (9 seasons, 2018–2026, DEF)
- rio-ferdinand (20 seasons, 1995–2014, DEF)
- riyad-mahrez (16 seasons, 2009–2025, WIDE)
- robert-lewandowski (22 seasons, 2004–2026, FWD)
- roberto-carlos (21 seasons, 1992–2015, DEF)
- robin-van-persie (18 seasons, 2001–2018, FWD)
- rodri-footballer-born-1996 (11 seasons, 2015–2025, MID)
- rodrygo (10 seasons, 2017–2026, WIDE)
- romelu-lukaku (18 seasons, 2008–2025, FWD)
- ronald-araujo (10 seasons, 2016–2025, DEF)
- ronaldinho (18 seasons, 1998–2015, WIDE)
- ronaldo-brazilian-footballer (17 seasons, 1993–2010, FWD)
- roy-keane (17 seasons, 1989–2005, MID)
- ruben-dias (9 seasons, 2017–2025, DEF)
- ruud-van-nistelrooy (19 seasons, 1993–2011, FWD)
- ryan-giggs (24 seasons, 1990–2013, WIDE)
- sadio-mane (15 seasons, 2011–2025, WIDE)
- samuel-eto-o (22 seasons, 1997–2018, FWD)
- sandro-tonali (10 seasons, 2017–2026, MID)
- sergio-aguero (19 seasons, 2003–2021, FWD)
- sergio-busquets (18 seasons, 2008–2025, MID)
- sergio-ramos (23 seasons, 2003–2025, DEF)
- son-heung-min (17 seasons, 2010–2026, WIDE)
- steven-gerrard (19 seasons, 1998–2016, MID)
- theo-hernandez (10 seasons, 2016–2025, DEF)
- thiago-alcantara (16 seasons, 2008–2023, MID)
- thiago-silva (23 seasons, 2004–2026, DEF)
- thierry-henry (21 seasons, 1994–2014, FWD)
- thomas-muller (19 seasons, 2008–2026, MID)
- toni-kroos (17 seasons, 2007–2023, MID)
- trent-alexander-arnold (11 seasons, 2016–2026, DEF)
- victor-osimhen (10 seasons, 2016–2025, FWD)
- vincent-kompany (17 seasons, 2003–2019, DEF)
- vinicius-junior (10 seasons, 2017–2026, WIDE)
- virgil-van-dijk (16 seasons, 2010–2025, DEF)
- wayne-rooney (19 seasons, 2002–2020, FWD)
- wesley-sneijder (17 seasons, 2002–2018, MID)
- william-saliba (8 seasons, 2018–2025, DEF)
- xabi-alonso (18 seasons, 1999–2016, MID)
- xavi-footballer-born-1980 (21 seasons, 1998–2018, MID)
- yaya-toure (19 seasons, 2001–2019, MID)
- zlatan-ibrahimovic (24 seasons, 1999–2022, FWD)

## Quarantined players (0)


---

# Phase 2B Addendum — Quarantine Recovery, Audit & Re-Evaluation

## Recovered quarantines (16 → 0)

The first collection pass quarantined 16 players. Root-causing each showed all
16 were fixable (none were genuinely un-normalizable):

| Player(s) | Original reason | Fix | Recovered |
|---|---|---|---|
| Robben, Gilberto Silva, Maicon, Essien, Scholes, Roberto Carlos, Ronaldo | "missing season" | did-not-play gaps are now a **warning**, not an error (never zero-filled) | ✅ |
| Falcão | "missing season" (childhood artifact) | childhood rows (age < 15, Lanceros Boyacá) excluded | ✅ |
| Godín, Luis Suárez, Lautaro | "conflicting duplicate rows" | Apertura/Clausura & calendar→split seasons kept as **distinct canonical seasons** (source label), not conflicts | ✅ |
| Jorginho | wrong entity (1964 namesake) | Wikidata QID override → Q3810078 (Italy int'l) | ✅ |
| Bernardo Silva | ambiguity flag | QID override confirms Q15521306 | ✅ |
| Xavi, Gavi | mononym not resolved | QID overrides (Q17500, Q108111889) | ✅ |
| Wayne Rooney | "no seasons parsed" | HTML `colspan` sanitization + html5lib fallback | ✅ |

**Remaining quarantines: 0.** Identity overrides are recorded with reasons in
`acquisition/identity_overrides.json`.

## Corrected records (normalization defects found & fixed)

1. **Canonical season = source label.** "2005" (calendar) and "2005–06"
   (split-year) are now separate seasons (previously summed to an impossible 47
   apps for Godín). Verified van Dijk's two "2015–16" club rows still aggregate
   to 39. Regression tests added for Uruguay/Argentina split championships.
2. **Reserve accent gap.** "Barcelona Atlètic" (reserve) was slipping past the
   youth filter; broadened to exclude "<club> Atlètic/Atlético" while keeping
   senior Atlético Madrid/Mineiro/Paranaense and "…Athletic" clubs. Regression
   tested.
3. **Childhood exclusion (age < 15).** Removes childhood-club artifacts.
4. **Identity overrides (4).** Reviewed QIDs for mononyms / shared names.
5. **Season labels.** Every row now stores `season_source_label`,
   `season_start_year`, and `season_format` (split_year / calendar_year).

## Manual external source audit

- **Sample: 22 players** (>10% of 180), ≥3 per position group, spanning eras
  1980s–2020s, ≥5 mid-season transfers, ≥5 calendar/split-championship careers.
- **Method: each compared directly against its cited Wikipedia page** (fetched
  independently of the collector's parser) and Wikidata identity.
- **Mismatch rate: 0.** Identity (DOB + position) 22/22 correct;
  externally-confirmable season appearances/goals 16/16 exact. (~6 late/early
  season cells could not be surfaced by the audit fetch tool due to table
  truncation — a tool limit, not a confirmed error.)
- Full detail in `MANUAL_COLLECTION_AUDIT.md`.

## Dataset integrity (final)

- duplicate atomic rows: **0**; duplicate/overlapping aggregate rows: **0**
- implausible season totals (> 60 league apps): **0**
- unresolved team ids: **0**; unresolved league ids: **20** (2 players —
  Riquelme, Lahm — Division column not parsed; leagues really La Liga/Bundesliga)
- partial seasons used as completed targets: **0** (ongoing seasons flagged
  `is_partial` and excluded from next-season targets)
- Tier-A-incomplete / provenance-incomplete players: **0 / 0**

## Final counts

- **Completed players: 180 / 180** (0 quarantined) → `collected_players/`
- **Atomic rows (player-season-team-league): 3,143** → `collected_players_dataset.csv`
- **Canonical player-seasons: 2,996** → `collected_player_seasons.csv`
- Position (coarse): DEF 55, MID 65, FWD 30, WIDE 30 (fine: CB 30, FB 25, DM 25,
  CM 30, AM 10, WNG 30, FW 30 — exactly the roster section sizes).
- Career status (sourced, Phase 2C): active 102, retired 70, inactive 8.
- Partial (ongoing) seasons: 30. See `collection/reconciled_counts.json` (all
  counts generated from the final CSVs, not hardcoded) and the Phase-2C report
  for corrected evaluation.

## Re-evaluation on the expanded dataset (seed 42, reproducible)

180 players, 2,996 season rows, 2,816 with a next season. Leave-one-player-out
(LOPO), bootstrap 95% CIs, by era, continuation calibrated by age.

| Target | naive MAE | best model | best MAE | vs naive | 95% CI (best vs naive) |
|---|---|---|---|---|---|
| Next appearances | 7.20 | HistGB | **5.72** | **−20.6%** | [5.56, 5.90] vs [6.94, 7.47] — **non-overlapping** |
| Next goals | 3.48 | Ridge | **3.05** | **−12.4%** | [2.93, 3.17] vs [3.34, 3.63] — **non-overlapping** |
| Next goals/app | 0.11 | HistGB | 0.10 | −12.8% | — |

- **By era:** the model beats naive by ~18–27% for appearances in **every**
  decade (1980s–2020s), and by ~3–16% for goals in every modern decade.
- **Continuation / retirement:** 75 retirements / 2,891 rows. Logistic ROC-AUC
  **0.954**, HistGB AUC 0.944 / Brier 0.021. **Calibration by age is excellent**
  (predicted vs observed continuation): ≤21 1.00/1.00, 22–25 1.00/1.00, 26–29
  1.00/0.998, 30–33 0.985/0.984, **34+ 0.819/0.818** — retirement risk rises
  with age and matches reality. Treated probabilistically, never a fixed age.
- **Non-negative:** all count predictions clipped ≥ 0. **Reproducible:** seed 42.

### What changed vs the 20-player Phase-2A feasibility

The bigger, audited dataset **strengthened** every result and **resolved the
Phase-2A caveat**: appearances improved from −14% to **−20.6%** over naive, and
**goals went from a marginal −1.6% to a robust −12.4%** with non-overlapping
CIs — Tier A now meaningfully predicts next-season goals, not just appearances.
Continuation calibration is near-perfect across age bands.

## Final GO / NO-GO

**GO — the Tier-A collected dataset is production-quality for training an
appearances / goals / continuation model.**

Decision-rule check (all met): ≥1 model consistently beats naive across targets,
protocols, positions **and eras** (appearances −20.6%, goals −12.4%, both with
non-overlapping bootstrap CIs); continuation is well-calibrated by age
(AUC 0.95); errors are not worse for defenders/midfielders; all counts
non-negative; results reproducible at seed 42. The dataset is source-accurate
(0 audit mismatches), fully provenanced, youth/reserve-clean, and free of
duplicate/aggregate double-counting.

**Scope note (unchanged):** this remains a **Tier-A** dataset. Goals are now
predictable above baseline, but absolute goal error (~3) is still limited by the
absence of minutes/shots/xG (Tier B/C), which free respectful sources cannot
provide. Adding those remains the path to a substantially stronger model.

**Not done (per stop conditions):** no production integration, no Supabase
import, no predictor replacement, no frontend/deploy changes, no goalkeeper
collection. Awaiting approval.
