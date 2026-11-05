"""Incremental load into SQLite.

- Postings are upserted on (source, external_id): new ones are inserted, edited ones updated.
- first_seen / last_seen record when we first and most recently saw each posting.
- A posting missing from its company's feed is marked closed, but only if that company's
  feed was fetched successfully in this run (a failed request must not close every job).
- Each run is logged with its counts; rejected rows are stored with the reason.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Job
from .transform.skills import category

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY,
    source          TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    company         TEXT NOT NULL,
    title           TEXT NOT NULL,
    role_family     TEXT,
    seniority       TEXT,
    employment_type TEXT,
    city            TEXT,
    region          TEXT,
    country         TEXT,
    remote          INTEGER NOT NULL DEFAULT 0,
    workplace       TEXT,
    salary_min      REAL,
    salary_max      REAL,
    currency        TEXT,
    pay_period      TEXT,
    posted_at       TEXT,
    url             TEXT,
    description     TEXT,
    content_hash    TEXT,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    closed_at       TEXT,
    UNIQUE (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs (company);
CREATE INDEX IF NOT EXISTS idx_jobs_family ON jobs (role_family, seniority);
CREATE INDEX IF NOT EXISTS idx_jobs_open ON jobs (closed_at);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id   INTEGER NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    skill    TEXT NOT NULL,
    category TEXT,
    PRIMARY KEY (job_id, skill)
);
CREATE INDEX IF NOT EXISTS idx_skills_skill ON job_skills (skill);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    fetched     INTEGER, valid INTEGER, rejected INTEGER,
    inserted    INTEGER, updated INTEGER, unchanged INTEGER, closed INTEGER,
    failed_sources TEXT
);

CREATE TABLE IF NOT EXISTS rejects (
    run_id      INTEGER REFERENCES runs (id),
    source      TEXT, external_id TEXT, company TEXT, title TEXT,
    reason      TEXT
);
"""

_COLS = ["source", "external_id", "company", "title", "role_family", "seniority", "employment_type",
         "city", "region", "country", "remote", "workplace", "salary_min", "salary_max", "currency",
         "pay_period", "posted_at", "url", "description", "content_hash"]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con


def start_run(con) -> int:
    cur = con.execute("INSERT INTO runs (started_at) VALUES (?)", (now(),))
    con.commit()
    return cur.lastrowid


def _values(job: Job) -> list:
    d = job.__dict__
    return [int(d[c]) if c == "remote" else d[c] for c in _COLS]


def load(con, run_id: int, jobs: list[Job], rejects, fetched_companies: set[str], failed: list[str], fetched: int) -> dict:
    ts = now()
    stats = {"inserted": 0, "updated": 0, "unchanged": 0, "closed": 0}
    seen_ids: list[int] = []

    with con:  # one transaction: the run either fully lands or not at all
        for job in jobs:
            row = con.execute(
                "SELECT id, content_hash, closed_at FROM jobs WHERE source = ? AND external_id = ?",
                (job.source, job.external_id),
            ).fetchone()
            if row is None:
                cur = con.execute(
                    f"INSERT INTO jobs ({', '.join(_COLS)}, first_seen, last_seen) "
                    f"VALUES ({', '.join('?' * len(_COLS))}, ?, ?)",
                    _values(job) + [ts, ts],
                )
                job_id = cur.lastrowid
                stats["inserted"] += 1
            else:
                job_id = row["id"]
                if row["content_hash"] != job.content_hash or row["closed_at"]:
                    con.execute(
                        f"UPDATE jobs SET {', '.join(c + ' = ?' for c in _COLS)}, last_seen = ?, closed_at = NULL "
                        "WHERE id = ?",
                        _values(job) + [ts, job_id],
                    )
                    stats["updated"] += 1
                else:
                    con.execute("UPDATE jobs SET last_seen = ? WHERE id = ?", (ts, job_id))
                    stats["unchanged"] += 1
            seen_ids.append(job_id)
            con.execute("DELETE FROM job_skills WHERE job_id = ?", (job_id,))
            con.executemany(
                "INSERT INTO job_skills (job_id, skill, category) VALUES (?, ?, ?)",
                [(job_id, s, category(s)) for s in job.skills],
            )

        # Close postings that vanished from feeds we fetched successfully.
        if fetched_companies:
            ph = ", ".join("?" * len(fetched_companies))
            id_ph = ", ".join("?" * len(seen_ids)) or "NULL"
            cur = con.execute(
                f"UPDATE jobs SET closed_at = ? WHERE closed_at IS NULL AND source != 'csv' "
                f"AND company IN ({ph}) AND id NOT IN ({id_ph})",
                [ts, *sorted(fetched_companies), *seen_ids],
            )
            stats["closed"] = cur.rowcount

        con.executemany(
            "INSERT INTO rejects (run_id, source, external_id, company, title, reason) VALUES (?, ?, ?, ?, ?, ?)",
            [(run_id, j.source, j.external_id, j.company, j.title, reason) for j, reason in rejects],
        )
        con.execute(
            "UPDATE runs SET finished_at = ?, fetched = ?, valid = ?, rejected = ?, inserted = ?, updated = ?, "
            "unchanged = ?, closed = ?, failed_sources = ? WHERE id = ?",
            (now(), fetched, len(jobs), len(rejects), stats["inserted"], stats["updated"],
             stats["unchanged"], stats["closed"], ", ".join(failed) or None, run_id),
        )
    return stats
