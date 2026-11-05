"""Standardise free-text locations into city, region, country and a remote flag.

"vancouver, bc", "Vancouver BC", "Vancouver, British Columbia, Canada" -> Vancouver, BC, Canada
"Remote - Canada", "Remote (Canada)"                               -> remote, country Canada
"""
from __future__ import annotations

import re

# city -> (region, country). Extend as new cities show up in the data.
CITIES = {
    "vancouver": ("BC", "Canada"), "burnaby": ("BC", "Canada"), "richmond": ("BC", "Canada"),
    "surrey": ("BC", "Canada"), "victoria": ("BC", "Canada"), "kelowna": ("BC", "Canada"),
    "toronto": ("ON", "Canada"), "waterloo": ("ON", "Canada"), "kitchener": ("ON", "Canada"),
    "ottawa": ("ON", "Canada"), "mississauga": ("ON", "Canada"), "markham": ("ON", "Canada"),
    "montreal": ("QC", "Canada"), "montréal": ("QC", "Canada"), "quebec city": ("QC", "Canada"),
    "calgary": ("AB", "Canada"), "edmonton": ("AB", "Canada"), "winnipeg": ("MB", "Canada"),
    "halifax": ("NS", "Canada"),
    "seattle": ("WA", "United States"), "bellevue": ("WA", "United States"),
    "redmond": ("WA", "United States"), "san francisco": ("CA", "United States"),
    "new york": ("NY", "United States"), "new york city": ("NY", "United States"),
    "austin": ("TX", "United States"), "boston": ("MA", "United States"),
    "chicago": ("IL", "United States"), "los angeles": ("CA", "United States"),
    "denver": ("CO", "United States"), "london": (None, "United Kingdom"),
}
CITY_ALIASES = {"nyc": "new york", "sf": "san francisco", "yvr": "vancouver", "mtl": "montreal"}
CITY_DISPLAY = {"montréal": "Montreal", "new york city": "New York"}

REGIONS = {
    "bc": "BC", "british columbia": "BC", "b.c.": "BC", "on": "ON", "ontario": "ON",
    "qc": "QC", "quebec": "QC", "québec": "QC", "ab": "AB", "alberta": "AB",
    "mb": "MB", "manitoba": "MB", "ns": "NS", "nova scotia": "NS",
    "wa": "WA", "washington": "WA", "ca": "CA", "california": "CA", "ny": "NY", "new york": "NY",
}
CANADIAN_REGIONS = {"BC", "ON", "QC", "AB", "MB", "NS", "SK", "NB", "NL", "PE"}
COUNTRIES = {
    "canada": "Canada", "ca": "Canada", "can": "Canada",
    "united states": "United States", "usa": "United States", "us": "United States",
    "u.s.": "United States", "united kingdom": "United Kingdom", "uk": "United Kingdom",
}
_REMOTE = re.compile(r"\bremote\b|\banywhere\b|work from home|\bwfh\b", re.I)
_HYBRID = re.compile(r"\bhybrid\b", re.I)


def _tokens(loc: str) -> list[str]:
    loc = re.sub(r"[()\[\]]", ",", loc.lower())
    return [t.strip(" .-") for t in re.split(r"[,/|;]|\s+-\s+", loc) if t.strip(" .-")]


def parse(location: str, workplace_hint: str = "") -> dict:
    """Return dict(city, region, country, remote, workplace)."""
    loc = (location or "").strip()
    hint = (workplace_hint or "").lower()
    remote = bool(_REMOTE.search(loc)) or "remote" in hint
    if "hybrid" in hint or _HYBRID.search(loc):
        workplace = "hybrid"
    elif remote:
        workplace = "remote"
    elif hint in ("onsite", "on-site", "in office", "office"):
        workplace = "onsite"
    else:
        workplace = "unknown"   # most feeds don't say; don't guess "onsite"

    city = region = country = None
    for tok in _tokens(loc):
        words = tok.split()
        # "vancouver bc" -> try "vancouver bc", then "vancouver" + region "bc"
        for n in range(len(words), 0, -1):
            head, tail = " ".join(words[:n]), " ".join(words[n:])
            head = CITY_ALIASES.get(head, head)
            if city is None and head in CITIES:
                city = CITY_DISPLAY.get(head, head.title())
                region, country = CITIES[head]
                if tail in REGIONS:
                    region = REGIONS[tail]
                break
            if region is None and head in REGIONS and not tail and city is None:
                region = REGIONS[head]
                break
            if country is None and head in COUNTRIES and not tail:
                country = COUNTRIES[head]
                break
    if country is None and region in CANADIAN_REGIONS:
        country = "Canada"
    return {"city": city, "region": region, "country": country, "remote": remote, "workplace": workplace}
