"""End-to-end tests on saved API responses: two snapshots of the same job boards, a few days apart."""
import shutil
import sqlite3
from pathlib import Path

import pytest

from jobetl import analyze, load, pipeline

HERE = Path(__file__).parent
COMPANIES = HERE.parent / "config" / "sample_companies.yaml"


@pytest.fixture
def db(tmp_path):
    return tmp_path / "jobs.db"


def rows(db, sql, *args):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def test_first_run_loads_and_rejects(db):
    stats = pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    assert stats["fetched"] == 14            # the unlisted Ashby job is never fetched
    assert stats["rejected"] == 3
    assert stats["inserted"] == 11
    reasons = sorted(r["reason"] for r in rows(db, "SELECT reason FROM rejects"))
    assert reasons == ["duplicate posting", "missing title", "older than a year"]


def test_values_are_normalised(db):
    pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    intern = rows(db, "SELECT * FROM jobs WHERE external_id = '4101'")[0]
    assert intern["city"] == "Vancouver" and intern["seniority"] == "intern"
    assert (intern["salary_min"], intern["salary_max"], intern["pay_period"]) == (79000, 91500, "hour")
    skills = {r["skill"] for r in rows(db, "SELECT skill FROM job_skills WHERE job_id = ?", intern["id"])}
    assert {"Python", "SQL", "Airflow", "Snowflake", "dbt"} <= skills


def test_second_run_is_incremental(db):
    pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    stats = pipeline.run(COMPANIES, db, HERE / "fixtures/run2")
    assert stats["inserted"] == 1    # new ML new-grad role
    assert stats["updated"] == 1     # intern posting edited (pay changed)
    assert stats["closed"] == 1      # senior data engineer removed from the feed
    closed = rows(db, "SELECT title FROM jobs WHERE closed_at IS NOT NULL")
    assert closed == [{"title": "Senior Data Engineer"}]
    edited = rows(db, "SELECT salary_min, first_seen, last_seen FROM jobs WHERE external_id = '4101'")[0]
    assert edited["salary_min"] == 83200


def test_failed_source_does_not_close_its_jobs(db, tmp_path):
    pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    partial = tmp_path / "partial"
    shutil.copytree(HERE / "fixtures/run1", partial)
    (partial / "lever_cascade.json").unlink()        # simulate Lever being down
    stats = pipeline.run(COMPANIES, db, partial)
    assert stats["failed"] == ["lever:cascade"]
    assert stats["closed"] == 0
    assert rows(db, "SELECT COUNT(*) AS n FROM jobs WHERE company = 'Cascade Energy' AND closed_at IS NULL")[0]["n"] == 3


def test_rerun_with_same_data_changes_nothing(db):
    pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    stats = pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    assert (stats["inserted"], stats["updated"], stats["closed"]) == (0, 0, 0)
    assert stats["unchanged"] == 11


def test_report_builds(db):
    pipeline.run(COMPANIES, db, HERE / "fixtures/run1")
    con = load.connect(db)
    report = analyze.build_report(con)
    con.close()
    assert "Most requested skills" in report and "| Python |" in report
