"""Command line entry point.

python -m jobetl run                 # fetch live postings for config/companies.yaml
python -m jobetl run --offline       # use saved sample responses (no network needed)
python -m jobetl check-sources       # test every configured job board without loading anything
python -m jobetl report              # write reports/report.md from the database
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import analyze, load, pipeline
from .http import make_session
from .sources import ADAPTERS

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    p = argparse.ArgumentParser(prog="jobetl", description="Job market ETL pipeline")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="extract, transform, validate and load")
    r.add_argument("--companies", default=ROOT / "config/companies.yaml")
    r.add_argument("--db", default=ROOT / "data/jobs.db")
    r.add_argument("--offline", action="store_true", help="use saved responses in data/sample instead of the network")
    r.add_argument("--csv", action="append", default=[], help="also load a CSV of hand-collected postings")
    r.add_argument("--report", action="store_true", help="write the report after loading")

    c = sub.add_parser("check-sources", help="check each configured job board responds")
    c.add_argument("--companies", default=ROOT / "config/companies.yaml")

    rep = sub.add_parser("report", help="write reports/report.md")
    rep.add_argument("--db", default=ROOT / "data/jobs.db")
    rep.add_argument("--out", default=ROOT / "reports/report.md")

    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(message)s")

    if a.cmd == "run":
        companies = ROOT / "config/sample_companies.yaml" if a.offline and a.companies == ROOT / "config/companies.yaml" else a.companies
        stats = pipeline.run(companies, a.db, ROOT / "data/sample" if a.offline else None, a.csv)
        print(f"\nfetched {stats['fetched']}  valid {stats['valid']}  rejected {stats['rejected']}  |  "
              f"new {stats['inserted']}  updated {stats['updated']}  unchanged {stats['unchanged']}  "
              f"closed {stats['closed']}")
        if stats["failed"]:
            print("failed sources:", ", ".join(stats["failed"]))
        if a.report:
            _write_report(a.db, ROOT / "reports/report.md")

    elif a.cmd == "check-sources":
        session = make_session()
        for comp in pipeline.read_companies(a.companies):
            label = f"{comp['ats']}:{comp['slug']}"
            try:
                n = len(ADAPTERS[comp["ats"]].fetch(comp["slug"], session))
                print(f"OK    {label:<32} {n} postings")
            except Exception as e:
                print(f"FAIL  {label:<32} {e}")

    elif a.cmd == "report":
        _write_report(a.db, a.out)


def _write_report(db, out):
    con = load.connect(db)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(analyze.build_report(con))
    con.close()
    print(f"report written to {out}")


if __name__ == "__main__":
    main()
