"""Load CRM data from mock samples, CRMArena benchmark (HF + org), or custom Salesforce."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from config import get_settings
from services.crmarena_data import (
    BENCHMARK_ORG_CREDENTIALS,
    BENCHMARK_SOQL,
    fetch_benchmark_frames,
    load_benchmark_tasks,
    load_cached_frames,
    load_cached_tasks,
    save_cached_frames,
    save_cached_tasks,
)

logger = logging.getLogger(__name__)


def _sample_opportunities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Id": "006001", "Name": "Acme Enterprise", "StageName": "Prospecting", "Amount": 25000},
            {"Id": "006002", "Name": "Globex Renewal", "StageName": "Negotiation", "Amount": 120000},
            {"Id": "006003", "Name": "Initech Pilot", "StageName": "Closed Won", "Amount": 45000},
        ]
    )


def _sample_accounts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Id": "001001", "Name": "TechCorp", "Industry": "Technology", "AnnualRevenue": 5000000, "BillingCountry": "USA"},
            {"Id": "001002", "Name": "FinBank", "Industry": "Finance", "AnnualRevenue": 12000000, "BillingCountry": "UK"},
            {"Id": "001003", "Name": "RetailX", "Industry": "Retail", "AnnualRevenue": 800000, "BillingCountry": "USA"},
        ]
    )


OBJECT_FRAMES: dict[str, callable] = {
    "Opportunity": _sample_opportunities,
    "Account": _sample_accounts,
    "Lead": lambda: pd.DataFrame(
        [
            {"Id": "00Q001", "Name": "Jane Doe", "Status": "Open", "Company": "NewCo"},
            {"Id": "00Q002", "Name": "John Smith", "Status": "Working", "Company": "Beta LLC"},
        ]
    ),
    "Case": lambda: pd.DataFrame(
        [
            {"Id": "500001", "Subject": "Login issue", "Status": "Open", "Priority": "High", "AccountId": "001001"},
            {"Id": "500002", "Subject": "Billing question", "Status": "Closed", "Priority": "Low", "AccountId": "001002"},
        ]
    ),
}


class CRMIngestService:
    """Provides DataFrames per Salesforce object name."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._frames: dict[str, pd.DataFrame] = {}
        self._benchmark_tasks: pd.DataFrame = pd.DataFrame()
        self.data_source: str = "mock"
        self.record_counts: dict[str, int] = {}

    def load_all(self) -> None:
        mode = self._settings.crm_data_mode.lower()
        if mode == "huggingface":
            self._load_huggingface()
        elif mode == "salesforce":
            self._load_salesforce()
        else:
            self._load_mock()

    def _resolve_credentials(self, *, use_benchmark_defaults: bool) -> dict[str, str]:
        if self._settings.sf_username:
            return {
                "username": self._settings.sf_username,
                "password": self._settings.sf_password,
                "security_token": self._settings.sf_security_token,
                "domain": self._settings.sf_domain or "login",
            }
        if use_benchmark_defaults:
            return dict(BENCHMARK_ORG_CREDENTIALS)
        raise ValueError("Salesforce credentials required (set SF_USERNAME in .env)")

    def _load_mock(self) -> None:
        for name, factory in OBJECT_FRAMES.items():
            self._frames[name] = factory()
        self.data_source = "mock"
        self._update_counts()
        logger.info("Loaded mock CRM data for %s objects", len(self._frames))

    def _load_huggingface(self) -> None:
        """CRMArena: HF benchmark tasks + live records from the public benchmark Salesforce org."""
        ttl = self._settings.cache_ttl_seconds
        try:
            tasks = load_cached_tasks(ttl)
            if tasks is None:
                tasks = load_benchmark_tasks()
                save_cached_tasks(tasks)
            self._benchmark_tasks = tasks

            frames = load_cached_frames(ttl)
            if frames is None:
                creds = self._resolve_credentials(use_benchmark_defaults=True)
                frames = fetch_benchmark_frames(
                    username=creds["username"],
                    password=creds["password"],
                    security_token=creds["security_token"],
                    domain=creds["domain"],
                    limit=self._settings.max_page_size,
                )
                save_cached_frames(frames)

            if not frames.get("Account", pd.DataFrame()).empty:
                self._frames = frames
                self.data_source = "crmarena_benchmark_org"
                self._update_counts()
                logger.info(
                    "Loaded CRMArena benchmark org (%s accounts, %s cases, %s tasks from HF)",
                    self.record_counts.get("Account", 0),
                    self.record_counts.get("Case", 0),
                    len(self._benchmark_tasks),
                )
                return

            logger.warning("CRMArena org returned no accounts; falling back to mock data")
        except Exception as exc:  # noqa: BLE001
            logger.warning("CRMArena benchmark load failed (%s); falling back to mock data", exc)

        self._load_mock()
        self.data_source = "mock_fallback"

    def _load_salesforce(self) -> None:
        try:
            creds = self._resolve_credentials(use_benchmark_defaults=False)
            from simple_salesforce import Salesforce

            sf = Salesforce(
                username=creds["username"],
                password=creds["password"],
                security_token=creds["security_token"],
                domain=creds["domain"],
            )
            limit = self._settings.max_page_size
            for object_name in ("Account", "Opportunity", "Case", "Order", "Contact", "Lead"):
                if object_name not in BENCHMARK_SOQL and object_name == "Opportunity":
                    soql = (
                        f"SELECT Id, Name, StageName, Amount, AccountId FROM Opportunity "
                        f"ORDER BY CreatedDate DESC LIMIT {limit}"
                    )
                elif object_name in BENCHMARK_SOQL:
                    soql = BENCHMARK_SOQL[object_name].format(limit=limit)
                else:
                    continue
                try:
                    records = sf.query(soql)["records"]
                    rows = [{k: v for k, v in r.items() if k != "attributes"} for r in records]
                    self._frames[object_name] = pd.DataFrame(rows)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Skipping %s on custom org: %s", object_name, exc)
            if self._frames.get("Account") is not None and not self._frames["Account"].empty:
                self.data_source = "salesforce_org"
                self._update_counts()
                logger.info("Loaded custom Salesforce org data")
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Salesforce load failed (%s); falling back to mock", exc)
        self._load_mock()
        self.data_source = "mock_fallback"

    def _update_counts(self) -> None:
        self.record_counts = {name: len(df) for name, df in self._frames.items() if not df.empty}

    def get_frame(self, object_name: str) -> pd.DataFrame:
        if object_name not in self._frames:
            if object_name in OBJECT_FRAMES:
                self._frames[object_name] = OBJECT_FRAMES[object_name]()
            else:
                return pd.DataFrame()
        return self._frames[object_name].copy()

    def get_benchmark_tasks(self) -> pd.DataFrame:
        return self._benchmark_tasks.copy()

    def all_frames(self) -> dict[str, pd.DataFrame]:
        return {k: v.copy() for k, v in self._frames.items()}


_ingest: CRMIngestService | None = None


def get_ingest_service() -> CRMIngestService:
    global _ingest
    if _ingest is None:
        _ingest = CRMIngestService()
        _ingest.load_all()
    return _ingest


def reset_ingest_service() -> None:
    """Clear singleton (tests / config reload)."""
    global _ingest
    _ingest = None
