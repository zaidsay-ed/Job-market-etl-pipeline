"""Normalise pay to an annual range.

Handles structured pay from Lever and Ashby, and free text such as
"$40-$45/hr", "85,000 - 95,000 CAD", "$120K – $150K", "CA$6,500 per month".
Hourly pay is annualised at 2,080 hours (40 h x 52 weeks), monthly at x12.
"""
from __future__ import annotations

import re

HOURS_PER_YEAR = 2080
MULTIPLIER = {"hour": HOURS_PER_YEAR, "month": 12, "year": 1}

# Plausible annual bounds; anything outside is treated as a parsing mistake.
MIN_ANNUAL, MAX_ANNUAL = 10_000, 1_000_000

_CUR = r"(?:CA\$|C\$|US\$|CAD|USD|\$|£|€)"
_NUM = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?"
# One amount or a range: "$40", "$40-$45", "85,000 to 95,000", "$120K – $150K"
_RANGE = re.compile(
    rf"(?P<cur1>{_CUR})?\s*(?P<a>{_NUM})\s*(?P<ak>[kK])?"
    rf"(?:\s*(?:-|–|—|to)\s*(?P<cur2>{_CUR})?\s*(?P<b>{_NUM})\s*(?P<bk>[kK])?)?"
)
_HOURLY = re.compile(r"(/\s*h(ou)?r\b|per\s+hour|hourly|an\s+hour|/hour)", re.I)
_MONTHLY = re.compile(r"(/\s*mo(nth)?\b|per\s+month|monthly)", re.I)
_YEARLY = re.compile(r"(/\s*y(ea)?r\b|per\s+year|annual|annually|a\s+year|salary)", re.I)
# Only look near words that signal pay, so "5 years of experience" or "401k" isn't read as salary.
_PAY_HINT = re.compile(r"(salary|pay|compensation|base|wage|range|\$|CAD|USD|/\s*h(ou)?r|per hour)", re.I)


def _to_number(num: str, k: str | None) -> float:
    v = float(num.replace(",", ""))
    return v * 1000 if k else v


def _currency(text: str, default: str | None) -> str | None:
    t = text.upper()
    if "CAD" in t or "CA$" in t or "C$" in t:
        return "CAD"
    if "USD" in t or "US$" in t:
        return "USD"
    if "£" in text:
        return "GBP"
    if "€" in text:
        return "EUR"
    return default


def _interval(text: str, lo: float) -> str:
    if _HOURLY.search(text):
        return "hour"
    if _MONTHLY.search(text):
        return "month"
    if _YEARLY.search(text):
        return "year"
    # No unit given: small numbers are hourly rates, large ones are annual.
    return "hour" if lo < 200 else "year"


def _annualise(lo, hi, interval):
    m = MULTIPLIER.get(interval or "year", 1)
    lo, hi = lo * m, hi * m
    if lo > hi:
        lo, hi = hi, lo
    if not (MIN_ANNUAL <= lo <= MAX_ANNUAL and MIN_ANNUAL <= hi <= MAX_ANNUAL):
        return None
    return round(lo, -2), round(hi, -2)


def parse_text(text: str, default_currency: str | None = None):
    """Return (min, max, currency, period) or None."""
    if not text:
        return None
    for line in re.split(r"[\n•|;]", text):
        if not _PAY_HINT.search(line):
            continue
        for m in _RANGE.finditer(line):
            if not (m.group("cur1") or m.group("cur2") or m.group("ak") or _PAY_HINT.search(line)):
                continue
            lo = _to_number(m.group("a"), m.group("ak"))
            hi = _to_number(m.group("b"), m.group("bk") or m.group("ak")) if m.group("b") else lo
            # "$120-150K": the k on the upper bound applies to the lower one too
            if m.group("bk") and not m.group("ak") and lo < 1000 <= hi:
                lo *= 1000
            if lo < 5 and not m.group("ak"):
                continue   # tiny numbers like "3" are years or counts, not pay
            span = line[max(0, m.start() - 20): m.end() + 25]
            interval = _interval(span, lo)
            res = _annualise(lo, hi, interval)
            if res:
                return res[0], res[1], _currency(span, default_currency), interval
    return None


def normalise(raw, default_currency: str | None = None):
    """Prefer structured pay from the source; fall back to free text, then the description."""
    if raw.salary_min or raw.salary_max:
        lo = raw.salary_min or raw.salary_max
        hi = raw.salary_max or raw.salary_min
        interval = raw.salary_interval or _interval(raw.salary_text or "", lo)
        res = _annualise(float(lo), float(hi), interval)
        if res:
            return res[0], res[1], raw.salary_currency or default_currency, interval
    for text in (raw.salary_text, raw.description):
        res = parse_text(text, default_currency)
        if res:
            return res
    return None
