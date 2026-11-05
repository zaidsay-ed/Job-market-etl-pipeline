"""CSV input, for hand-collected postings. Columns match the original version of this project:
job_title, company, location, salary, skills, posted_date, job_type, [description, url]
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from ..models import RawPosting


def read(path: str | Path) -> list[RawPosting]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = "|".join((row.get(k) or "").strip().lower() for k in ("company", "job_title", "location"))
            desc = row.get("description") or ""
            if row.get("skills"):
                desc = f"{desc}\nSkills: {row['skills']}".strip()
            out.append(RawPosting(
                source="csv",
                external_id=hashlib.sha1(key.encode()).hexdigest()[:16],
                company=(row.get("company") or "").strip(),
                title=(row.get("job_title") or "").strip(),
                location=row.get("location") or "",
                description=desc,
                url=row.get("url") or "",
                posted_at=row.get("posted_date") or None,
                workplace=row.get("job_type") or "",
                salary_text=row.get("salary") or "",
            ))
    return out
