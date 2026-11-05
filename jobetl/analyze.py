"""Run the SQL in jobetl/sql/ and write a Markdown report."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

SQL_DIR = Path(__file__).parent / "sql"


def query(con, name: str, **params) -> pd.DataFrame:
    sql = (SQL_DIR / f"{name}.sql").read_text()
    return pd.read_sql_query(sql, con, params=params or None)


def _md(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data yet._\n"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append(f"{v:,.0f}" if abs(v) >= 100 else f"{v:g}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def salary_medians(con) -> pd.DataFrame:
    df = query(con, "salaries")
    if df.empty:
        return df
    out = (df.groupby(["location", "role_family", "currency"], dropna=False)["salary_mid"]
             .agg(postings="count", median_salary="median")
             .reset_index()
             .sort_values(["postings", "median_salary"], ascending=False))
    return out[out["postings"] >= 1].head(15)


def build_report(con) -> str:
    runs = pd.read_sql_query("SELECT * FROM runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1", con)
    open_jobs = con.execute("SELECT COUNT(*) FROM jobs WHERE closed_at IS NULL").fetchone()[0]
    companies = con.execute("SELECT COUNT(DISTINCT company) FROM jobs WHERE closed_at IS NULL").fetchone()[0]

    parts = [f"# Job market report\n\nGenerated {date.today().isoformat()} from {open_jobs} open postings "
             f"at {companies} companies.\n"]
    if not runs.empty:
        r = runs.iloc[0]
        parts.append(
            f"Last run: fetched {r.fetched}, valid {r.valid}, rejected {r.rejected}; "
            f"{r.inserted} new, {r.updated} updated, {r.unchanged} unchanged, {r.closed} closed."
            + (f" Failed sources: {r.failed_sources}." if r.failed_sources else "") + "\n"
        )
    parts += [
        "## Most requested skills\n", _md(query(con, "top_skills", seniority=None)),
        "## Most requested skills for internships and co-ops\n", _md(query(con, "top_skills", seniority="intern")),
        "## Top skills by role family\n", _md(query(con, "skills_by_family")),
        "## Median annual salary by location and role\n",
        "Hourly pay is annualised at 2,080 hours; monthly at 12 months.\n\n", _md(salary_medians(con)),
        "## Companies hiring early-career roles\n", _md(query(con, "early_career_by_company")),
        "## New postings per week\n", _md(query(con, "postings_per_week")),
    ]
    return "\n".join(parts)
