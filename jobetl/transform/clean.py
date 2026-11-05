"""Turn a RawPosting into a normalised Job."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

from ..models import Job, RawPosting
from . import location, roles, salary, skills


def _title(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    # Fix all-lowercase or all-caps titles; keep normal titles exactly as written.
    if t.islower() or t.isupper():
        t = t.title()
        t = re.sub(r"\b(Ml|Ai|Bi|Etl|Sql|Qa|Sre|Ios|Ui|Ux)\b", lambda m: m.group(1).upper(), t)
    return t


def _date(s: str | None) -> str | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def clean(raw: RawPosting) -> Job:
    title = _title(raw.title)
    loc = location.parse(raw.location, raw.workplace)
    default_cur = {"Canada": "CAD", "United States": "USD"}.get(loc["country"] or "")
    pay = salary.normalise(raw, default_cur)
    emp = roles.employment_type(title, raw.employment_type, raw.description)
    job = Job(
        source=raw.source,
        external_id=raw.external_id,
        company=raw.company.strip(),
        title=title,
        url=raw.url,
        posted_at=_date(raw.posted_at),
        description=raw.description,
        city=loc["city"], region=loc["region"], country=loc["country"],
        remote=loc["remote"], workplace=loc["workplace"],
        employment_type=emp,
        seniority=roles.seniority(title, emp),
        role_family=roles.role_family(title),
        salary_min=pay[0] if pay else None,
        salary_max=pay[1] if pay else None,
        currency=pay[2] if pay else None,
        pay_period=pay[3] if pay else None,
        skills=skills.extract(f"{title}\n{raw.description}"),
    )
    # Changes to any of these mean the posting was edited and should be updated in the database.
    key = "|".join(str(x) for x in (job.title, job.description, raw.location, job.salary_min, job.salary_max))
    job.content_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    return job
