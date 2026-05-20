"""CRMArena benchmark: Hugging Face tasks + Salesforce org record export."""

from __future__ import annotations

import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import repo_root

logger = logging.getLogger(__name__)

# Public research org credentials (SalesforceAIResearch/CRMArena README).
BENCHMARK_ORG_CREDENTIALS: dict[str, str] = {
    "username": "kh.huang+00dws000004urq4@salesforce.com",
    "password": "crmarenatest0",
    "security_token": "ugvBSBv0ArI7dayfqUY0wMGu",
    "domain": "login",
}

# Objects available in the CRMArena benchmark org (Opportunity/Lead are not deployed).
BENCHMARK_SOQL: dict[str, str] = {
    "Account": (
        "SELECT Id, Name, Industry, AnnualRevenue, BillingCountry, NumberOfEmployees "
        "FROM Account ORDER BY Name LIMIT {limit}"
    ),
    "Case": (
        "SELECT Id, Subject, Status, Priority, AccountId "
        "FROM Case ORDER BY CreatedDate DESC LIMIT {limit}"
    ),
    "Contact": (
        "SELECT Id, Name, Email, AccountId "
        "FROM Contact ORDER BY Name LIMIT {limit}"
    ),
    "Order": (
        "SELECT Id, OrderNumber, Status, TotalAmount, AccountId "
        "FROM Order ORDER BY CreatedDate DESC LIMIT {limit}"
    ),
}

_CACHE_DIR = repo_root() / ".cache" / "crmarena"
_FRAMES_CACHE = _CACHE_DIR / "frames.pkl"
_TASKS_CACHE = _CACHE_DIR / "tasks.pkl"


def _records_to_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [{k: v for k, v in r.items() if k != "attributes"} for r in records]
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def load_benchmark_tasks() -> pd.DataFrame:
    """Load CRMArena evaluation tasks from Hugging Face."""
    from datasets import load_dataset

    ds = load_dataset("Salesforce/CRMArena", "CRMArena", split="test")
    return ds.to_pandas()


def fetch_benchmark_frames(
    username: str,
    password: str,
    security_token: str,
    domain: str = "login",
    limit: int = 500,
) -> dict[str, pd.DataFrame]:
    """Query live records from the CRMArena Salesforce benchmark org."""
    from simple_salesforce import Salesforce

    sf = Salesforce(
        username=username,
        password=password,
        security_token=security_token,
        domain=domain,
    )
    frames: dict[str, pd.DataFrame] = {}
    for object_name, soql_template in BENCHMARK_SOQL.items():
        soql = soql_template.format(limit=limit)
        try:
            result = sf.query(soql)
            frames[object_name] = _records_to_df(result.get("records", []))
            logger.info("CRMArena org: loaded %s %s rows", len(frames[object_name]), object_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CRMArena org: failed to load %s (%s)", object_name, exc)
            frames[object_name] = pd.DataFrame()
    return frames


def _cache_valid(path: Path, ttl_seconds: int) -> bool:
    if not path.is_file():
        return False
    age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    return age < ttl_seconds


def load_cached_frames(ttl_seconds: int) -> dict[str, pd.DataFrame] | None:
    if not _cache_valid(_FRAMES_CACHE, ttl_seconds):
        return None
    try:
        with _FRAMES_CACHE.open("rb") as f:
            data = pickle.load(f)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read CRMArena frame cache: %s", exc)
        return None


def save_cached_frames(frames: dict[str, pd.DataFrame]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with _FRAMES_CACHE.open("wb") as f:
        pickle.dump(frames, f)


def load_cached_tasks(ttl_seconds: int) -> pd.DataFrame | None:
    if not _cache_valid(_TASKS_CACHE, ttl_seconds):
        return None
    try:
        with _TASKS_CACHE.open("rb") as f:
            return pickle.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read CRMArena tasks cache: %s", exc)
        return None


def save_cached_tasks(tasks: pd.DataFrame) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with _TASKS_CACHE.open("wb") as f:
        pickle.dump(tasks, f)
