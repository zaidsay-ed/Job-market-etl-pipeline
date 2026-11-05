"""Shared record types.

RawPosting is what every source produces after parsing its own API format.
Job is the cleaned, normalised record that gets validated and loaded.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawPosting:
    source: str                      # "greenhouse" | "lever" | "ashby" | "csv"
    external_id: str                 # the posting's id in its source system
    company: str
    title: str
    location: str = ""
    description: str = ""            # plain text
    url: str = ""
    posted_at: str | None = None     # ISO 8601
    employment_type: str = ""        # as given by the source, e.g. "Intern", "FullTime"
    workplace: str = ""              # as given by the source, e.g. "remote", "Hybrid"
    salary_text: str = ""            # free-text pay, e.g. "$40-$45/hr"
    salary_min: float | None = None  # structured pay, when the source provides it
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_interval: str | None = None  # "year" | "month" | "hour"


@dataclass
class Job:
    source: str
    external_id: str
    company: str
    title: str
    url: str
    posted_at: str | None
    description: str
    # location
    city: str | None
    region: str | None
    country: str | None
    remote: bool
    workplace: str                   # "remote" | "hybrid" | "onsite" | "unknown"
    # role
    employment_type: str             # "internship" | "co-op" | "full-time" | "part-time" | "contract" | "unknown"
    seniority: str                   # "intern" | "new grad" | "junior" | "mid" | "senior" | "staff+"
    role_family: str                 # "data engineering" | "data science" | "machine learning" | ...
    # pay, annualised
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    pay_period: str | None           # the period the source quoted, before annualising
    skills: list[str] = field(default_factory=list)
    content_hash: str = ""
