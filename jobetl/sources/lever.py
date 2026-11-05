"""Lever public Postings API.

GET https://api.lever.co/v0/postings/{slug}?mode=json
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..http import get_json
from ..models import RawPosting
from ..transform.text import html_to_text

URL = "https://api.lever.co/v0/postings/{slug}"

_INTERVALS = {
    "per-year-salary": "year",
    "per-month-salary": "month",
    "per-hour-wage": "hour",
}


def fetch(slug: str, session) -> list[dict]:
    data = get_json(session, URL.format(slug=slug), params={"mode": "json"})
    return data if isinstance(data, list) else []


def parse(item: dict, company: str) -> RawPosting:
    cats = item.get("categories") or {}
    parts = [item.get("descriptionPlain") or html_to_text(item.get("description"))]
    for lst in item.get("lists") or []:
        parts.append(f"{lst.get('text', '')}\n{html_to_text(lst.get('content'))}")
    parts.append(item.get("additionalPlain") or "")

    created = item.get("createdAt")
    posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat() if created else None

    sal = item.get("salaryRange") or {}
    return RawPosting(
        source="lever",
        external_id=str(item["id"]),
        company=company,
        title=(item.get("text") or "").strip(),
        location=cats.get("location") or ", ".join(cats.get("allLocations") or []),
        description="\n\n".join(p for p in parts if p).strip(),
        url=item.get("hostedUrl", ""),
        posted_at=posted,
        employment_type=cats.get("commitment", ""),
        workplace=item.get("workplaceType", ""),
        salary_text=item.get("salaryDescriptionPlain") or "",
        salary_min=sal.get("min"),
        salary_max=sal.get("max"),
        salary_currency=sal.get("currency"),
        salary_interval=_INTERVALS.get(sal.get("interval", "")),
    )
