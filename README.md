# Job Market ETL Pipeline

An ETL pipeline that pulls live job postings from companies' public job boards, cleans and normalises them, and loads them into SQLite so I can answer questions like *which skills do Canadian data internships ask for* and *what do they pay*.

```
Greenhouse ─┐                        ┌─ salary → annual range, currency
Lever      ─┼─► extract ─► transform ┼─ location → city / region / country / remote ─► validate ─► load (SQLite) ─► SQL report
Ashby      ─┤                        ├─ skills extracted from free text
CSV        ─┘                        └─ role family, seniority, employment type
```

## What it does

- **Extract** from the public job-board APIs of [Greenhouse](https://developers.greenhouse.io/job-board.html), [Lever](https://github.com/lever/postings-api) and [Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api), plus hand-collected CSVs. Requests have timeouts, retries with backoff, and a pause between calls. One failing job board is logged and skipped, not fatal.
- **Transform**
  - **Salary:** structured pay where the source has it, otherwise parsed from text (`$40-$45/hr`, `85,000 - 95,000 CAD`, `$120K – $150K`, `CA$6,500 per month`). Annualised (hourly × 2,080, monthly × 12), with currency detected and implausible values dropped.
  - **Location:** `vancouver, bc`, `Vancouver BC` and `Vancouver, British Columbia, Canada` all become *Vancouver, BC, Canada*; `Remote - Canada` becomes remote + Canada.
  - **Skills:** about 50 skills with aliases (`k8s` → Kubernetes, `Postgres` → PostgreSQL), matched as whole words. Ambiguous words like *Go*, *R* and *Excel* only count when used as a skill, so "go to market" or "excel at" don't.
  - **Role:** employment type (internship, co-op, full-time…), seniority (intern → staff+) and role family (data engineering, data science, ML, analytics, software).
- **Validate:** drops missing titles, duplicate IDs, the same job cross-posted twice, and postings over a year old. Every dropped row is stored in a `rejects` table with the reason.
- **Load incrementally:** upserts on `(source, external_id)`; tracks `first_seen` / `last_seen`; updates edited postings (detected with a content hash); marks postings that disappear as closed. A company whose feed failed to load is never closed out. Each run is one transaction and is logged in `runs`.
- **Analyse:** SQL in [`jobetl/sql/`](jobetl/sql) produces a Markdown report: top skills overall and for internships, top skills per role family (window functions), median pay by location and role, companies hiring early-career roles, and new postings per week. See [`reports/sample_report.md`](reports/sample_report.md).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# No network needed: uses saved API responses for four fictional companies
python -m jobetl run --offline --report

# Live data for the companies in config/companies.yaml
python -m jobetl check-sources        # confirm each job board responds
python -m jobetl run --report         # writes data/jobs.db and reports/report.md

# Run it again later: only new and changed postings are written; removed ones are closed
python -m jobetl run --report

# Add hand-collected postings
python -m jobetl run --csv data/sample/hand_collected.csv
```

Add or remove companies in [`config/companies.yaml`](config/companies.yaml). The slug is in the company's job links, e.g. `boards.greenhouse.io/<slug>`.

## Database

| table | holds |
|---|---|
| `jobs` | one row per posting: normalised fields, description, `first_seen`, `last_seen`, `closed_at` |
| `job_skills` | `(job_id, skill, category)`, one row per skill per posting |
| `runs` | counts for every run: fetched, valid, rejected, inserted, updated, unchanged, closed, failed sources |
| `rejects` | every dropped row and why |

## Tests

```bash
python -m pytest -q
```

45 tests cover salary, location, skill and role parsing (including the false positives above), plus end-to-end runs over two snapshots of the same job boards: first load, an incremental second load (1 new, 1 edited, 1 closed), a rerun that changes nothing, and a job board outage that must not close its jobs. GitHub Actions runs them on every push.

## Design decisions

- **Public job-board APIs, not scraping.** Greenhouse, Lever and Ashby publish these endpoints so postings can be listed elsewhere. They return full descriptions, and using them avoids breaking LinkedIn's or Indeed's terms.
- **SQLite.** One file, zero setup, and enough for tens of thousands of postings. The load layer uses plain SQL, so moving to Postgres is a connection change plus small syntax tweaks.
- **Rules before ML for parsing.** Salary, location and skill parsing are deterministic and tested, so every value can be explained. Unknown formats come out as `NULL` rather than as a wrong guess.
- **Closing needs a successful fetch.** Without that check, a single timeout would mark a whole company's jobs as closed.

## Limitations

- Hourly pay assumes full-time hours (2,080 per year), which overstates part-time roles.
- Currency defaults to the posting's country when the text only says `$`.
- The skill list is hand-curated, so new tools need adding to [`skills.py`](jobetl/transform/skills.py).

## Next

Making the cleaned postings searchable in plain English with retrieval-augmented generation (RAG): "Which Vancouver data internships want Airflow, and what do they pay?", answered with citations to the actual postings.
