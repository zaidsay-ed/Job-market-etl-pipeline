"""Classify a posting's employment type, seniority and role family from its title and fields."""
from __future__ import annotations

import re


def employment_type(title: str, raw_type: str, description: str = "") -> str:
    t = f"{title} {raw_type}".lower()
    if re.search(r"co-?op", t):
        return "co-op"
    if re.search(r"\bintern(ship)?\b", t):
        return "internship"
    if re.search(r"contract|temporary|fixed[- ]term", t):
        return "contract"
    if re.search(r"part[- ]?time", t):
        return "part-time"
    if re.search(r"full[- ]?time|permanent|regular", t):
        return "full-time"
    return "full-time" if title else "unknown"


def seniority(title: str, employment: str) -> str:
    t = title.lower()
    if employment in ("internship", "co-op"):
        return "intern"
    if re.search(r"new grad|graduate|university grad|entry[- ]level", t):
        return "new grad"
    if re.search(r"\b(staff|principal|distinguished|director|head of|vp)\b", t):
        return "staff+"
    if re.search(r"\b(senior|sr\.?|lead)\b", t):
        return "senior"
    if re.search(r"\b(junior|jr\.?|associate)\b|\b(i|1)\b$", t):
        return "junior"
    return "mid"


# Checked in order; the first match wins.
_FAMILIES = [
    ("data engineering", r"data engineer|analytics engineer|data platform|etl|data infrastructure"),
    ("machine learning", r"machine learning|\bml\b|\bai\b|deep learning|computer vision|nlp|applied scientist"),
    ("data science", r"data scien|research scientist|quantitative|statistician"),
    ("analytics", r"data analyst|business intelligence|\bbi\b|analytics|business analyst"),
    ("software engineering", r"software|developer|engineer|backend|back-end|frontend|front-end|full[- ]?stack|sre|devops|platform"),
]


def role_family(title: str) -> str:
    t = title.lower()
    for name, pat in _FAMILIES:
        if re.search(pat, t):
            return name
    return "other"
