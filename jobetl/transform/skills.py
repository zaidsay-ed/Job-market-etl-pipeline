"""Extract skills from free text using a curated taxonomy with aliases.

Matching is whole-word and case-insensitive. Names that are also everyday words
("Go", "R", "Excel") use stricter, case-sensitive patterns so that "go to market",
"R&D" or "excel at" don't count.
"""
from __future__ import annotations

import re

# canonical name -> (category, aliases)
TAXONOMY: dict[str, tuple[str, list[str]]] = {
    # languages
    "Python": ("language", ["python"]),
    "SQL": ("language", ["sql"]),
    "Java": ("language", ["java"]),
    "Scala": ("language", ["scala"]),
    "TypeScript": ("language", ["typescript"]),
    "JavaScript": ("language", ["javascript", "node.js", "nodejs"]),
    "Go": ("language", []),          # see SPECIAL
    "Rust": ("language", ["rust"]),
    "C++": ("language", ["c\\+\\+"]),
    "C#": ("language", ["c#", "\\.net"]),
    "R": ("language", []),           # see SPECIAL
    "Kotlin": ("language", ["kotlin"]),
    # data engineering
    "Spark": ("data", ["spark", "pyspark"]),
    "Airflow": ("data", ["airflow"]),
    "dbt": ("data", ["dbt"]),
    "Kafka": ("data", ["kafka"]),
    "Snowflake": ("data", ["snowflake"]),
    "BigQuery": ("data", ["bigquery"]),
    "Redshift": ("data", ["redshift"]),
    "Databricks": ("data", ["databricks"]),
    "Flink": ("data", ["flink"]),
    "ETL": ("data", ["etl", "elt", "data pipelines?"]),
    "Pandas": ("data", ["pandas"]),
    "PostgreSQL": ("database", ["postgres", "postgresql"]),
    "MySQL": ("database", ["mysql"]),
    "MongoDB": ("database", ["mongodb", "mongo"]),
    "Redis": ("database", ["redis"]),
    # ML
    "scikit-learn": ("ml", ["scikit-learn", "sklearn"]),
    "PyTorch": ("ml", ["pytorch"]),
    "TensorFlow": ("ml", ["tensorflow"]),
    "LLMs": ("ml", ["llms?", "large language models?", "gpt", "rag"]),
    "NumPy": ("ml", ["numpy"]),
    # cloud and infra
    "AWS": ("cloud", ["aws", "amazon web services", "s3", "ec2"]),
    "GCP": ("cloud", ["gcp", "google cloud"]),
    "Azure": ("cloud", ["azure"]),
    "Docker": ("infra", ["docker"]),
    "Kubernetes": ("infra", ["kubernetes", "k8s"]),
    "Terraform": ("infra", ["terraform"]),
    "CI/CD": ("infra", ["ci/cd", "continuous integration", "github actions"]),
    # web
    "React": ("web", ["react", "react.js", "reactjs"]),
    "FastAPI": ("web", ["fastapi"]),
    "Django": ("web", ["django"]),
    "GraphQL": ("web", ["graphql"]),
    "REST APIs": ("web", ["rest apis?", "restful"]),
    # BI
    "Tableau": ("bi", ["tableau"]),
    "Power BI": ("bi", ["power ?bi"]),
    "Looker": ("bi", ["looker"]),
    "Excel": ("bi", []),            # see SPECIAL
}


# Case-sensitive patterns for skills whose names are also ordinary words.
_LIST_BEFORE = r"(?:(?<=[,(/:])|(?<=[,(/:] )|(?<=\band )|(?<=\bor )|(?<=\bin )|(?<=\bwith ))"
_LIST_AFTER = r"(?=\s*(?:[,)/;.]|and\b|or\b|$))"
SPECIAL = {
    "Go": re.compile(r"\b(?i:golang)\b|" + _LIST_BEFORE + r"Go" + _LIST_AFTER),
    "R": re.compile(_LIST_BEFORE + r"R" + _LIST_AFTER),
    "Excel": re.compile(r"\b(?:Microsoft |MS )?Excel\b(?! at\b| in\b| as\b)"),
}


def _compile():
    pats = {}
    for name, (_, aliases) in TAXONOMY.items():
        if name in SPECIAL:
            pats[name] = SPECIAL[name]
            continue
        alts = "|".join(a if any(ch in a for ch in "\\?+") else re.escape(a) for a in aliases)
        pats[name] = re.compile(rf"(?<![\w.+#-])(?:{alts})(?![\w+#])", re.I)
    return pats


_PATTERNS = _compile()


def extract(text: str) -> list[str]:
    if not text:
        return []
    return sorted(name for name, pat in _PATTERNS.items() if pat.search(text))


def category(skill: str) -> str:
    return TAXONOMY.get(skill, ("other", []))[0]
