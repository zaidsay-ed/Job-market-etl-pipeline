"""HTTP session with timeouts, retries and polite pacing for public job-board APIs."""
from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "job-market-etl/1.0 (+https://github.com/zaidsay-ed/Job-market-etl-pipeline)"
TIMEOUT = 20          # seconds per request
MIN_INTERVAL = 0.5    # seconds between requests, so we never hammer a job board


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    retry = Retry(
        total=3,
        backoff_factor=1.0,                       # waits 1s, 2s, 4s between attempts
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


_last_request = 0.0


def get_json(session: requests.Session, url: str, params: dict | None = None):
    global _last_request
    wait = MIN_INTERVAL - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    resp = session.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
