"""Source adapters. Each one knows one job board's public API format.

fetch(slug, session) -> list of raw API items
parse(item, company) -> RawPosting
"""
from . import ashby, greenhouse, lever

ADAPTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
}
