"""Ashby public Job Posting API.

GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true
"""
from __future__ import annotations

from ..http import get_json
from ..models import RawPosting
from ..transform.text import html_to_text

URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

_INTERVALS = {"1 YEAR": "year", "1 MONTH": "month", "1 HOUR": "hour"}


def fetch(slug: str, session) -> list[dict]:
    data = get_json(session, URL.format(slug=slug), params={"includeCompensation": "true"})
    return [j for j in data.get("jobs", []) if j.get("isListed", True)]


def parse(item: dict, company: str) -> RawPosting:
    comp = item.get("compensation") or {}
    salary = next(
        (c for c in comp.get("summaryComponents") or [] if c.get("compensationType") == "Salary"),
        {},
    )
    locs = [item.get("location") or ""] + [
        s.get("location", "") for s in item.get("secondaryLocations") or []
    ]
    workplace = item.get("workplaceType") or ("Remote" if item.get("isRemote") else "")
    return RawPosting(
        source="ashby",
        external_id=str(item["id"]),
        company=company,
        title=(item.get("title") or "").strip(),
        location=", ".join(l for l in locs if l),
        description=item.get("descriptionPlain") or html_to_text(item.get("descriptionHtml")),
        url=item.get("jobUrl", ""),
        posted_at=item.get("publishedAt"),
        employment_type=item.get("employmentType", ""),
        workplace=workplace,
        salary_text=comp.get("compensationTierSummary") or "",
        salary_min=salary.get("minValue"),
        salary_max=salary.get("maxValue"),
        salary_currency=salary.get("currencyCode"),
        salary_interval=_INTERVALS.get(salary.get("interval", "")),
    )
