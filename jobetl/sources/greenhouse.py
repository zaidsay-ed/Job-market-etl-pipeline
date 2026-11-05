"""Greenhouse public Job Board API.

GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
No key needed; this endpoint exists so companies' postings can be listed elsewhere.
"""
from __future__ import annotations

from ..http import get_json
from ..models import RawPosting
from ..transform.text import html_to_text

URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch(slug: str, session) -> list[dict]:
    data = get_json(session, URL.format(slug=slug), params={"content": "true"})
    return data.get("jobs", [])


def parse(item: dict, company: str) -> RawPosting:
    loc = (item.get("location") or {}).get("name", "")
    offices = ", ".join(o.get("name", "") for o in item.get("offices") or [] if o.get("name"))
    return RawPosting(
        source="greenhouse",
        external_id=str(item["id"]),
        company=company,
        title=(item.get("title") or "").strip(),
        location=loc or offices,
        description=html_to_text(item.get("content")),
        url=item.get("absolute_url", ""),
        posted_at=item.get("first_published") or item.get("updated_at"),
        # Greenhouse has no structured pay or job type; both are parsed from the text later.
    )
