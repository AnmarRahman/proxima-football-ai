"""Wikidata identity resolution and verification.

Resolves a roster name to a single Wikidata entity that is verifiably a
footballer, and returns its canonical English Wikipedia title (from sitelinks)
so collection is tied to an identity, not a guessed page name. Ambiguous or
unverifiable matches are reported so the caller can quarantine them.

Honest access only (Wikidata public API, identifying User-Agent, cached,
rate-limited via the Phase-1 client). No circumvention.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ACQ = Path(__file__).resolve().parents[1] / "acquisition"
sys.path.insert(0, str(ACQ))

from sources.base import CachingHTTPClient, SourceBlocked, SourceUnavailable  # noqa: E402

WD_API = "https://www.wikidata.org/w/api.php"
FOOTBALLER_OCCUPATIONS = {"Q937857"}   # association football player
HUMAN = "Q5"
OVERRIDES_PATH = ACQ / "identity_overrides.json"


def load_overrides(path=OVERRIDES_PATH):
    if not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("overrides", {})


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def _parse_time(claims, pid):
    try:
        t = claims[pid][0]["mainsnak"]["datavalue"]["value"]["time"]  # +1987-02-02T..
        y, m, d = t[1:5], t[6:8], t[9:11]
        m = "01" if m == "00" else m
        d = "01" if d == "00" else d
        return f"{y}-{m}-{d}"
    except (KeyError, IndexError, TypeError):
        return None


def _first_qid(claims, pid):
    try:
        return claims[pid][0]["mainsnak"]["datavalue"]["value"]["id"]
    except (KeyError, IndexError, TypeError):
        return None


def _all_qids(claims, pid):
    out = []
    for c in claims.get(pid, []) or []:
        try:
            out.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except (KeyError, TypeError):
            pass
    return out


def choose_candidate(cands):
    """Pure decision over resolved candidates. Each cand needs keys:
    footballer, is_human, enwiki, name_match, sitelinks. Returns
    (best_or_None, status, note)."""
    fb = [c for c in cands if c.get("footballer") and c.get("is_human") and c.get("enwiki")]
    if not fb:
        return None, "not_footballer", "no candidate verified as a footballer with an enwiki page"
    fb = sorted(fb, key=lambda c: (c["name_match"], c["sitelinks"]), reverse=True)
    best = fb[0]
    for other in fb[1:]:
        if other["name_match"] >= best["name_match"] - 0.001 and \
                other["sitelinks"] >= 0.5 * best["sitelinks"]:
            return best, "ambiguous", "multiple prominent footballers match this name"
    if best["name_match"] < 0.5:
        return best, "ambiguous", f"best name match only {best['name_match']}"
    return best, "ok", ""


class WikidataIdentity:
    def __init__(self, cache_dir=None, min_delay=1.0, overrides=None):
        kw = {"min_delay": min_delay}
        if cache_dir:
            kw["cache_dir"] = cache_dir
        self.http = CachingHTTPClient("wikidata", **kw)
        self._label_cache = {}
        self.overrides = load_overrides() if overrides is None else overrides

    def _api(self, params):
        params = dict(params); params["format"] = "json"
        resp = self.http.get(WD_API, params=params, ext="json")
        return json.loads(resp["text"]), resp["retrieved_at"]

    def search(self, name, limit=7):
        data, _ = self._api({"action": "wbsearchentities", "search": name,
                             "language": "en", "type": "item", "limit": limit})
        return [{"id": r["id"], "label": r.get("label", ""),
                 "description": r.get("description", "")} for r in data.get("search", [])]

    def entities(self, qids):
        if not qids:
            return {}
        data, _ = self._api({"action": "wbgetentities", "ids": "|".join(qids),
                             "props": "claims|labels|sitelinks|descriptions"})
        return data.get("entities", {})

    def labels(self, qids):
        need = [q for q in qids if q and q not in self._label_cache]
        if need:
            data, _ = self._api({"action": "wbgetentities", "ids": "|".join(need),
                                 "props": "labels", "languages": "en"})
            for q, ent in data.get("entities", {}).items():
                try:
                    self._label_cache[q] = ent["labels"]["en"]["value"]
                except KeyError:
                    self._label_cache[q] = None
        return {q: self._label_cache.get(q) for q in qids}

    def resolve(self, name):
        """Return an identity dict with status ok/ambiguous/not_found/not_footballer."""
        out = {"requested_name": name, "wikidata_id": None, "enwiki_title": None,
               "birth_date": None, "nationality": None, "nationality_qid": None,
               "position_label": None, "occupation_footballer": False,
               "sitelinks": 0, "status": "not_found", "note": "", "candidates": []}

        ov = self.overrides.get(name)
        if ov:
            out.update({
                "wikidata_id": ov.get("wikidata_id"), "enwiki_title": ov.get("enwiki_title"),
                "birth_date": ov.get("birth_date"), "nationality": ov.get("nationality"),
                "position_label": ov.get("position_label"), "occupation_footballer": True,
                "status": "ok", "note": f"manual identity override: {ov.get('reason', '')}",
                "override": True, "expected_clubs": ov.get("expected_clubs"),
            })
            return out

        try:
            hits = self.search(name)
        except (SourceBlocked, SourceUnavailable) as exc:
            out["status"] = "error"; out["note"] = f"search failed: {exc}"
            return out
        if not hits:
            out["note"] = "no Wikidata search hits"
            return out

        ents = self.entities([h["id"] for h in hits])
        cands = []
        want = _norm(name)
        for h in hits:
            ent = ents.get(h["id"])
            if not ent:
                continue
            claims = ent.get("claims", {})
            instance = _all_qids(claims, "P31")
            occ = _all_qids(claims, "P106")
            has_pos = bool(claims.get("P413"))
            has_club = bool(claims.get("P54"))
            is_human = HUMAN in instance
            footballer = bool(FOOTBALLER_OCCUPATIONS & set(occ)) or has_pos or has_club
            label = ent.get("labels", {}).get("en", {}).get("value", h["label"])
            enwiki = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
            nlab = _norm(label)
            want_tokens = set(want.split())
            match = (len(want_tokens & set(nlab.split())) / len(want_tokens)) if want_tokens else 0.0
            cands.append({
                "qid": h["id"], "label": label, "enwiki": enwiki,
                "is_human": is_human, "footballer": footballer,
                "occ_footballer": bool(FOOTBALLER_OCCUPATIONS & set(occ)),
                "sitelinks": len(ent.get("sitelinks", {})),
                "name_match": round(match, 2),
                "birth_date": _parse_time(claims, "P569"),
                "nationality_qid": _first_qid(claims, "P27"),
                "position_qid": _first_qid(claims, "P413"),
                "description": h.get("description", ""),
            })
        out["candidates"] = [{k: c[k] for k in ("qid", "label", "footballer",
                              "sitelinks", "name_match")} for c in cands]

        best, status, note = choose_candidate(cands)
        out["status"], out["note"] = status, note
        if best is None:
            return out

        labels = self.labels([best["nationality_qid"], best["position_qid"]])
        out.update({
            "wikidata_id": best["qid"], "enwiki_title": best["enwiki"],
            "birth_date": best["birth_date"],
            "nationality_qid": best["nationality_qid"],
            "nationality": labels.get(best["nationality_qid"]),
            "position_label": labels.get(best["position_qid"]),
            "occupation_footballer": best["occ_footballer"],
            "sitelinks": best["sitelinks"],
        })
        # verification completeness
        missing = [f for f in ("birth_date", "nationality") if not out[f]]
        if out["status"] == "ok" and missing:
            out["status"] = "ambiguous"
            out["note"] = f"missing verification fields: {missing}"
        return out


if __name__ == "__main__":
    wd = WikidataIdentity()
    for n in ["Gerard Pique", "Pepe", "Marquinhos", "David Alaba", "Rafael Leao", "Sergio Ramos"]:
        r = wd.resolve(n)
        print(f"{n:16} -> {r['status']:13} {r['wikidata_id']} '{r['enwiki_title']}' "
              f"dob={r['birth_date']} nat={r['nationality']} note={r['note']}")
