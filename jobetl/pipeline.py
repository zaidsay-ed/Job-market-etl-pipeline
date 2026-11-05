"""Extract -> transform -> validate -> load, for every configured company."""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import yaml

from . import load as loader
from .http import make_session
from .sources import ADAPTERS, csv_source
from .transform.clean import clean
from .validate import validate

log = logging.getLogger("jobetl")


def read_companies(path: str | Path) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return [c for c in data.get("companies", []) if c.get("ats") in ADAPTERS and c.get("slug")]


def extract(companies: list[dict], offline_dir: Path | None = None):
    """Fetch raw items per company. In offline mode, read saved API responses instead of the network.

    Returns (raw postings, companies fetched successfully, failed source labels).
    """
    raws, ok, failed = [], set(), []
    session = None if offline_dir else make_session()
    for c in companies:
        adapter = ADAPTERS[c["ats"]]
        label = f"{c['ats']}:{c['slug']}"
        try:
            if offline_dir:
                path = offline_dir / f"{c['ats']}_{c['slug']}.json"
                data = json.loads(path.read_text())
                items = data.get("jobs", data) if isinstance(data, dict) else data
                if c["ats"] == "ashby":
                    items = [j for j in items if j.get("isListed", True)]
            else:
                items = adapter.fetch(c["slug"], session)
            parsed = [adapter.parse(item, c["name"]) for item in items]
            raws.extend(parsed)
            ok.add(c["name"])
            log.info("%-28s %4d postings", label, len(parsed))
        except Exception as e:  # one broken source must not stop the run
            failed.append(label)
            log.warning("%-28s FAILED: %s", label, e)
    return raws, ok, failed


def run(companies_file: str | Path, db_path: str | Path, offline_dir: str | Path | None = None,
        csv_files: list[str] | None = None) -> dict:
    companies = read_companies(companies_file)
    raws, ok, failed = extract(companies, Path(offline_dir) if offline_dir else None)
    for f in csv_files or []:
        raws.extend(csv_source.read(f))

    jobs = [clean(r) for r in raws]
    # Saved sample data never changes, so judge its age against its own newest posting, not today.
    as_of = None
    if offline_dir:
        dates = [j.posted_at for j in jobs if j.posted_at]
        as_of = date.fromisoformat(max(dates)) if dates else None
    valid, rejects = validate(jobs, as_of)

    con = loader.connect(db_path)
    run_id = loader.start_run(con)
    stats = loader.load(con, run_id, valid, rejects, ok, failed, fetched=len(raws))
    con.close()

    stats.update(fetched=len(raws), valid=len(valid), rejected=len(rejects), failed=failed)
    return stats
