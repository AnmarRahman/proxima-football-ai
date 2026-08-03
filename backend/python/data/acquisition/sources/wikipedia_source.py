"""Wikipedia (+ Wikidata) adapter: bio and league appearances/goals.

Honest access only: standard GET with an identifying User-Agent against the
public Wikipedia article and the Wikidata API. No parsing that requires
circumventing access controls. Provides Tier A fields:
  bio       -> birth_date, nationality, position, height_cm
  seasons   -> per club-season league appearances and goals (competition-level)
Assists, minutes, xG, etc. are NOT on Wikipedia and are left to other sources.
"""

import io
import json
import re

import pandas as pd
from bs4 import BeautifulSoup

from .base import CachingHTTPClient, SourceBlocked, SourceUnavailable, BioBlock, StatBlock

WIKI_ARTICLE = "https://en.wikipedia.org/wiki/{title}"
WD_API = "https://www.wikidata.org/w/api.php"


def _clean(text):
    return re.sub(r"\[[^\]]*\]", "", str(text)).strip()


def _season_start_year(raw):
    m = re.search(r"(\d{4})", str(raw))
    return int(m.group(1)) if m else None


def _to_int(v):
    s = _clean(v)
    return int(s) if re.fullmatch(r"\d+", s) else None


class WikipediaSource:
    provider = "Wikipedia"

    def __init__(self, cache_dir=None, min_delay=2.0):
        kw = {"min_delay": min_delay}
        if cache_dir:
            kw["cache_dir"] = cache_dir
        self.http = CachingHTTPClient("wikipedia", **kw)
        wd_kw = {"min_delay": 1.0}
        if cache_dir:
            wd_kw["cache_dir"] = cache_dir
        self.wd = CachingHTTPClient("wikidata", **wd_kw)

    # -- low level -------------------------------------------------------
    def _article(self, title):
        url = WIKI_ARTICLE.format(title=title.replace(" ", "_"))
        resp = self.http.get(url, ext="html")
        return url, resp["text"], resp["retrieved_at"]

    def _wikidata_nationality(self, html):
        m = re.search(r"wikidata\.org\\?/entity\\?/(Q\d+)", html)
        if not m:
            return None
        qid = m.group(1)
        try:
            r = self.wd.get(WD_API, params={"action": "wbgetentities", "ids": qid,
                                            "props": "claims", "format": "json"}, ext="json")
            claims = json.loads(r["text"])
            p27 = claims["entities"][qid]["claims"].get("P27")
            if not p27:
                return None
            country_qid = p27[0]["mainsnak"]["datavalue"]["value"]["id"]
            r2 = self.wd.get(WD_API, params={"action": "wbgetentities", "ids": country_qid,
                                             "props": "labels", "languages": "en",
                                             "format": "json"}, ext="json")
            labels = json.loads(r2["text"])
            return labels["entities"][country_qid]["labels"]["en"]["value"]
        except (SourceBlocked, SourceUnavailable, KeyError, ValueError):
            return None

    # -- parsing ---------------------------------------------------------
    def parse_bio(self, html):
        soup = BeautifulSoup(html, "lxml")
        fields = {}
        bday = soup.select_one("span.bday")
        if bday:
            fields["birth_date"] = bday.get_text(strip=True)
        infobox = soup.select_one("table.infobox")
        if infobox:
            for row in infobox.select("tr"):
                th = row.find("th")
                td = row.find("td")
                if not th or not td:
                    continue
                label = th.get_text(" ", strip=True).lower()
                if label.startswith("position"):
                    fields["position"] = _clean(td.get_text(" ", strip=True))
                elif label.startswith("height"):
                    m = re.search(r"(\d+\.\d+)\s*m", td.get_text(" ", strip=True))
                    if m:
                        fields["height_cm"] = int(round(float(m.group(1)) * 100))
        nat = self._wikidata_nationality(html)
        if nat:
            fields["nationality"] = nat
        return fields

    @staticmethod
    def _read_tables(html):
        """Robust read_html: sanitize malformed colspan/rowspan (some articles,
        e.g. Wayne Rooney, ship colspan='2"' which crashes the default parser)
        and fall back to html5lib when the default flavor fails."""
        clean = re.sub(r'(colspan|rowspan)\s*=\s*["\']?(\d+)[^\s>]*',
                       r'\1="\2"', html, flags=re.IGNORECASE)
        for kwargs in ({}, {"flavor": "html5lib"}):
            try:
                return pd.read_html(io.StringIO(clean), **kwargs)
            except (ValueError, Exception):  # noqa: BLE001 - try next flavor
                continue
        return []

    @staticmethod
    def _season_format(raw):
        return "split_year" if re.search(r"\d{4}\s*[–\-/]\s*\d{2,4}", str(raw)) \
            else "calendar_year"

    def parse_career(self, html):
        """Return list of season records with source + canonical season labels:
        {season (start year), season_source_label, season_format, club,
         competition, appearances, goals}."""
        tables = self._read_tables(html)
        records = []
        for t in tables:
            cols = list(t.columns)
            flat = [" ".join(str(x) for x in c) if isinstance(c, tuple) else str(c) for c in cols]
            if not any("Apps" in f for f in flat):
                continue

            def find(pred):
                for c, f in zip(cols, flat):
                    if pred(f):
                        return c
                return None
            club_c = find(lambda f: f.startswith("Club"))
            season_c = find(lambda f: f.startswith("Season"))
            div_c = find(lambda f: f.startswith("League") and "Division" in f)
            apps_c = find(lambda f: f.startswith("League") and f.endswith("Apps"))
            goals_c = find(lambda f: f.startswith("League") and f.endswith("Goals"))
            if not (club_c and season_c and apps_c and goals_c):
                continue
            for _, r in t.iterrows():
                club = _clean(r[club_c])
                if not club or re.search(r"total|career", club, re.I):
                    continue
                raw_season = _clean(r[season_c])
                year = _season_start_year(raw_season)
                if year is None:
                    continue
                apps = _to_int(r[apps_c])
                goals = _to_int(r[goals_c])
                if apps is None:
                    continue
                records.append({
                    "season": year,
                    "season_source_label": raw_season,
                    "season_format": self._season_format(raw_season),
                    "club": club,
                    "competition": _clean(r[div_c]) if div_c else None,
                    "appearances": apps, "goals": goals,
                })
            if records:
                break  # first club-career table only
        return records

    def fetch_article_meta(self, title):
        """Fetch an article and return career records plus source metadata
        (URL, retrieval date, and Wikipedia revision id where present)."""
        url, html, retrieved = self._article(title)
        m = re.search(r'"wgRevisionId":(\d+)', html)
        revision = int(m.group(1)) if m else None
        return {"url": url, "retrieved_at": retrieved, "revision": revision,
                "career": self.parse_career(html)}

    # -- public ----------------------------------------------------------
    def get_player(self, title):
        """Return (bio_block, [StatBlock,...]). Raises SourceBlocked if blocked."""
        url, html, retrieved = self._article(title)
        bio = BioBlock(self.provider, url, retrieved, self.parse_bio(html))
        blocks = []
        for rec in self.parse_career(html):
            blocks.append(StatBlock(
                provider=self.provider, url=url, retrieved_at=retrieved,
                season=rec["season"], team=rec["club"], competition=rec["competition"],
                fields={"appearances": rec["appearances"], "goals": rec["goals"]},
            ))
        return bio, blocks
