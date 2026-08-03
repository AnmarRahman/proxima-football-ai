"""Shared HTTP client and data structures for free-source acquisition adapters.

Design goals (all mandated by the pilot brief):
  * Respectful, legal automation only. We DO NOT bypass access controls.
  * Rate-limit every outbound request (per-client min delay).
  * Cache every successful response to disk so pages are fetched at most once.
  * Exponential backoff for transient server errors (5xx, timeouts).
  * STOP immediately on 401/403/429/CAPTCHA/access-denied -- record the source
    as blocked and move on. We never retry past a block.
  * Clear User-Agent identifying the project and a contact address.

Nothing here estimates or invents data; adapters return only what a source
actually provides, each value tagged with provenance.
"""

import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

USER_AGENT = (
    "ProximaFootballAI-ResearchPilot/0.1 "
    "(non-commercial research; contact: wamied@gmail.com)"
)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"

# Statuses that mean "you are being blocked / access controlled" -> never retry.
BLOCK_STATUSES = {401, 403, 429, 451}
# Transient server-side errors worth a bounded backoff retry.
TRANSIENT_STATUSES = {500, 502, 503, 504}


class SourceBlocked(Exception):
    """Raised when a source refuses automated access (401/403/429/CAPTCHA).

    The pilot records this as `unavailable` and continues with other sources;
    we never attempt to circumvent it."""

    def __init__(self, url, status, detail=""):
        self.url = url
        self.status = status
        self.detail = detail
        super().__init__(f"blocked {status} for {url} {detail}".strip())


class SourceUnavailable(Exception):
    """Raised for non-block failures (network error, 404, parse gap)."""


def today_iso():
    return date.today().isoformat()


def _looks_like_captcha(text):
    """Detect an interstitial anti-bot CHALLENGE page (not article content).

    Deliberately narrow: matches only well-known challenge interstitials so we
    never false-positive on normal pages (e.g. a Wikipedia article that merely
    contains the word 'captcha'). Real HTTP blocks are handled by BLOCK_STATUSES.
    """
    if not text:
        return False
    lowered = text[:4000].lower()
    signatures = (
        "just a moment...",                # Cloudflare
        "checking your browser before",    # Cloudflare
        "attention required! | cloudflare",
        "cf-chl-",                         # Cloudflare challenge token
        "please verify you are a human",
        "enable javascript and cookies to continue",
        "ddos protection by",
    )
    return any(s in lowered for s in signatures)


class CachingHTTPClient:
    """GET with on-disk caching, rate limiting, and backoff.

    Cache layout (raw responses, kept separate from normalized output):
        <cache_dir>/<provider>/<sha1>.<ext>        raw body
        <cache_dir>/<provider>/<sha1>.meta.json    {url, status, retrieved_at}
    """

    def __init__(self, provider, cache_dir=DEFAULT_CACHE_DIR, min_delay=3.0,
                 max_retries=3, timeout=20, session=None):
        self.provider = provider
        self.cache_dir = Path(cache_dir) / provider
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_delay = float(min_delay)
        self.max_retries = int(max_retries)
        self.timeout = timeout
        self._last_request_ts = 0.0
        self.hits = 0        # served from disk cache
        self.misses = 0      # fetched over the network
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    @property
    def n_requests(self):
        return self.hits + self.misses

    @property
    def cache_hit_rate(self):
        return round(self.hits / self.n_requests, 3) if self.n_requests else 0.0

    def _key(self, url, params, ext):
        raw = url + "?" + json.dumps(params or {}, sort_keys=True)
        h = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.{ext}", self.cache_dir / f"{h}.meta.json"

    def _respect_delay(self):
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

    def get(self, url, params=None, ext="html", force=False):
        """Return {text, status, url, retrieved_at, from_cache}.

        Raises SourceBlocked on access control, SourceUnavailable otherwise."""
        body_path, meta_path = self._key(url, params, ext)
        if body_path.exists() and meta_path.exists() and not force:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.update(text=body_path.read_text(encoding="utf-8"), from_cache=True)
            self.hits += 1
            return meta

        last_exc = None
        for attempt in range(self.max_retries):
            self._respect_delay()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(min(2 ** attempt, 8))  # backoff on network error
                self._last_request_ts = time.monotonic()
                continue
            self._last_request_ts = time.monotonic()

            if resp.status_code in BLOCK_STATUSES or _looks_like_captcha(resp.text):
                raise SourceBlocked(url, resp.status_code,
                                    "captcha/anti-bot" if _looks_like_captcha(resp.text) else "")
            if resp.status_code in TRANSIENT_STATUSES:
                time.sleep(min(2 ** attempt, 8))  # exponential backoff
                last_exc = SourceUnavailable(f"HTTP {resp.status_code} for {url}")
                continue
            if resp.status_code != 200:
                raise SourceUnavailable(f"HTTP {resp.status_code} for {url}")

            retrieved_at = today_iso()
            meta = {"url": url, "status": resp.status_code,
                    "retrieved_at": retrieved_at,
                    "fetched_ts": datetime.now(timezone.utc).isoformat()}
            body_path.write_text(resp.text, encoding="utf-8")
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            meta.update(text=resp.text, from_cache=False)
            self.misses += 1
            return meta

        raise SourceUnavailable(f"exhausted retries for {url}: {last_exc}")


class StatBlock:
    """One source's contribution to a single (season, team, competition) row.

    `fields` holds only values the source actually provided (never null/invented).
    """

    def __init__(self, provider, url, retrieved_at, season, team, competition,
                 fields, team_id=None, league_id=None, position=None):
        self.provider = provider
        self.url = url
        self.retrieved_at = retrieved_at
        self.season = season
        self.team = team
        self.team_id = team_id
        self.competition = competition
        self.league_id = league_id
        self.position = position
        self.fields = {k: v for k, v in (fields or {}).items() if v is not None}

    def as_dict(self):
        return {
            "provider": self.provider, "url": self.url,
            "retrieved_at": self.retrieved_at, "season": self.season,
            "team": self.team, "team_id": self.team_id,
            "competition": self.competition, "league_id": self.league_id,
            "position": self.position, "fields": self.fields,
        }


class BioBlock:
    """Player-level identity from a source (e.g. Wikipedia)."""

    def __init__(self, provider, url, retrieved_at, fields):
        self.provider = provider
        self.url = url
        self.retrieved_at = retrieved_at
        self.fields = {k: v for k, v in (fields or {}).items() if v is not None}

    def as_dict(self):
        return {"provider": self.provider, "url": self.url,
                "retrieved_at": self.retrieved_at, "fields": self.fields}
