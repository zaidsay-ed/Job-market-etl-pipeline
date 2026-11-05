import pytest

from jobetl.models import RawPosting
from jobetl.transform import location, roles, salary, skills
from jobetl.transform.text import html_to_text


# ---------- salary ----------
@pytest.mark.parametrize("text, expected", [
    ("$40-$45/hr", (83200, 93600, "CAD", "hour")),
    ("Salary: 85,000 - 95,000 CAD", (85000, 95000, "CAD", "year")),
    ("$120K – $150K • Offers Equity", (120000, 150000, "CAD", "year")),
    ("The base pay range is $120-150K USD", (120000, 150000, "USD", "year")),
    ("CA$6,500 per month", (78000, 78000, "CAD", "month")),
    ("Hourly rate: 28 to 32 CAD", (58200, 66600, "CAD", "hour")),
    ("Compensation: 110000", (110000, 110000, "CAD", "year")),
])
def test_salary_from_text(text, expected):
    assert salary.parse_text(text, "CAD") == expected


@pytest.mark.parametrize("text", [
    "5+ years of experience and a 401k",
    "We have 3 offices and 200 engineers",
    "",
])
def test_salary_ignores_non_pay_numbers(text):
    assert salary.parse_text(text, "CAD") is None


def test_structured_salary_beats_text():
    raw = RawPosting("lever", "1", "Co", "Intern", salary_min=36, salary_max=42,
                     salary_currency="CAD", salary_interval="hour", description="Salary: $200,000")
    assert salary.normalise(raw) == (74900, 87400, "CAD", "hour")


def test_salary_out_of_range_is_rejected():
    assert salary.parse_text("Pay: $5,000,000 per year", "CAD") is None


# ---------- location ----------
@pytest.mark.parametrize("raw, city, region, country, remote", [
    ("vancouver, bc", "Vancouver", "BC", "Canada", False),
    ("Vancouver BC", "Vancouver", "BC", "Canada", False),
    ("Vancouver, British Columbia, Canada", "Vancouver", "BC", "Canada", False),
    ("Montréal", "Montreal", "QC", "Canada", False),
    ("Remote - Canada", None, None, "Canada", True),
    ("Remote (Canada)", None, None, "Canada", True),
    ("Seattle, WA", "Seattle", "WA", "United States", False),
    ("Ontario", None, "ON", "Canada", False),
])
def test_location(raw, city, region, country, remote):
    got = location.parse(raw)
    assert (got["city"], got["region"], got["country"], got["remote"]) == (city, region, country, remote)


def test_workplace_hint():
    assert location.parse("Vancouver, BC", "hybrid")["workplace"] == "hybrid"
    assert location.parse("Vancouver, BC")["workplace"] == "unknown"


# ---------- skills ----------
@pytest.mark.parametrize("text, expected", [
    ("Experience with Python, SQL and Go.", ["Go", "Python", "SQL"]),
    ("Spark/PySpark, Airflow, dbt", ["Airflow", "Spark", "dbt"]),
    ("Postgres or MySQL; k8s", ["Kubernetes", "MySQL", "PostgreSQL"]),
    ("Node.js and React", ["JavaScript", "React"]),
    ("Strong in R, Python", ["Python", "R"]),
    ("Advanced Excel skills", ["Excel"]),
])
def test_skills_found(text, expected):
    assert skills.extract(text) == expected


@pytest.mark.parametrize("text", [
    "We go to market fast", "Our R&D team", "You excel at communication", "lambda functions",
])
def test_skills_not_fooled_by_ordinary_words(text):
    assert skills.extract(text) == []


# ---------- roles ----------
@pytest.mark.parametrize("title, raw_type, emp, level, family", [
    ("Data Engineer Intern (Summer 2027)", "", "internship", "intern", "data engineering"),
    ("Data Analyst Co-op (4 months)", "", "co-op", "intern", "analytics"),
    ("Senior Data Engineer", "", "full-time", "senior", "data engineering"),
    ("Machine Learning Engineer, New Grad", "", "full-time", "new grad", "machine learning"),
    ("Quantitative Data Scientist", "FullTime", "full-time", "mid", "data science"),
    ("Staff Software Engineer", "", "full-time", "staff+", "software engineering"),
    ("Machine Learning Intern", "Intern", "internship", "intern", "machine learning"),
])
def test_roles(title, raw_type, emp, level, family):
    e = roles.employment_type(title, raw_type)
    assert (e, roles.seniority(title, e), roles.role_family(title)) == (emp, level, family)


# ---------- text ----------
def test_html_to_text_handles_greenhouse_escaped_html():
    s = "&lt;p&gt;Build &lt;strong&gt;pipelines&lt;/strong&gt;&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;"
    assert html_to_text(s) == "Build pipelines\n\n- Python"
