"""Validation and de-duplication. Every dropped row is kept with a reason, so nothing disappears silently."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .models import Job

MAX_AGE_DAYS = 365


def _key(job: Job) -> str:
    """Same company + same title + same city = the same job, even if posted twice."""
    title = re.sub(r"[^a-z0-9]+", " ", job.title.lower()).strip()
    return f"{job.company.lower()}|{title}|{(job.city or ('remote' if job.remote else '')).lower()}"


def validate(jobs: list[Job], as_of: date | None = None) -> tuple[list[Job], list[tuple[Job, str]]]:
    """as_of is the date used for the age check (defaults to today; the offline sample pins it)."""
    valid: list[Job] = []
    rejects: list[tuple[Job, str]] = []
    seen_ids: set[tuple[str, str]] = set()
    seen_keys: set[str] = set()
    oldest = ((as_of or date.today()) - timedelta(days=MAX_AGE_DAYS)).isoformat()

    for job in jobs:
        if not job.title:
            rejects.append((job, "missing title"))
        elif not job.company:
            rejects.append((job, "missing company"))
        elif (job.source, job.external_id) in seen_ids:
            rejects.append((job, "duplicate id"))
        elif _key(job) in seen_keys:
            rejects.append((job, "duplicate posting"))
        elif job.posted_at and job.posted_at < oldest:
            rejects.append((job, "older than a year"))
        elif job.salary_min and job.salary_max and job.salary_min > job.salary_max:
            rejects.append((job, "salary min above max"))
        else:
            seen_ids.add((job.source, job.external_id))
            seen_keys.add(_key(job))
            valid.append(job)
    return valid, rejects
