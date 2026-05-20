"""Load CRM data from mock samples, Hugging Face CRMArena, or Salesforce."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from config import get_settings

logger = logging.getLogger(__name__)


def _sample_opportunities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Id": "006001", "Name": "Acme Enterprise", "StageName": "Prospecting", "Amount": 25000},
            {"Id": "006002", "Name": "Globex Renewal", "StageName": "Negotiation", "Amount": 120000},
            {"Id": "006003", "Name": "Initech Pilot", "StageName": "Closed Won", "Amount": 45000},
            {"Id": "006004", "Name": "Umbrella Expansion", "StageName": "Qualification", "Amount": 80000},
            {"Id": "006005", "Name": "Stark Industries", "StageName": "Negotiation", "Amount": 200000},
            {"Id": "006006", "Name": "Wayne Analytics", "StageName": "Prospecting", "Amount": 15000},
        ]
    )


def _sample_accounts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Id": "001001", "Name": "TechCorp", "Industry": "Technology", "AnnualRevenue": 5000000, "BillingCountry": "USA"},
            {"Id": "001002", "Name": "FinBank", "Industry": "Finance", "AnnualRevenue": 12000000, "BillingCountry": "UK"},
            {"Id": "001003", "Name": "RetailX", "Industry": "Retail", "AnnualRevenue": 800000, "BillingCountry": "USA"},
            {"Id": "001004", "Name": "HealthPlus", "Industry": "Healthcare", "AnnualRevenue": 3500000, "BillingCountry": "Canada"},
            {"Id": "001005", "Name": "LogiMove", "Industry": "Logistics", "AnnualRevenue": 2200000, "BillingCountry": "Germany"},
            {"Id": "001006", "Name": "EduLearn", "Industry": "Education", "AnnualRevenue": 15000000, "BillingCountry": "USA"},
            {"Id": "001007", "Name": "MediaWave", "Industry": "Media", "AnnualRevenue": 4500000, "BillingCountry": "France"},
            {"Id": "001008", "Name": "GreenEnergy", "Industry": "Energy", "AnnualRevenue": 9000000, "BillingCountry": "USA"},
            {"Id": "001009", "Name": "AutoDrive", "Industry": "Automotive", "AnnualRevenue": 600000, "BillingCountry": "Japan"},
            {"Id": "001010", "Name": "CloudNine", "Industry": "Technology", "AnnualRevenue": 18000000, "BillingCountry": "USA"},
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
            {"Id": "500003", "Subject": "API latency", "Status": "Open", "Priority": "High", "AccountId": "001003"},
            {"Id": "500004", "Subject": "Onboarding delay", "Status": "Open", "Priority": "Medium", "AccountId": "001003"},
            {"Id": "500005", "Subject": "Feature request", "Status": "Open", "Priority": "Low", "AccountId": "001009"},
        ]
    ),
}


class CRMIngestService:
    """Provides DataFrames per Salesforce object name."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._frames: dict[str, pd.DataFrame] = {}

    def load_all(self) -> None:
        mode = self._settings.crm_data_mode.lower()
        if mode == "huggingface":
            self._load_huggingface()
        elif mode == "salesforce":
            self._load_salesforce()
        else:
            self._load_mock()

    def _load_mock(self) -> None:
        for name, factory in OBJECT_FRAMES.items():
            self._frames[name] = factory()
        logger.info("Loaded mock CRM data for %s objects", len(self._frames))

    def _load_huggingface(self) -> None:
        try:
            from datasets import load_dataset

            load_dataset("Salesforce/CRMArena", "CRMArena", split="test", streaming=True)
            logger.info("CRMArena dataset reachable; using mock aggregates for dashboard MVP")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hugging Face load failed (%s); falling back to mock data", exc)
        self._load_mock()

    def _load_salesforce(self) -> None:
        if not self._settings.sf_username:
            raise ValueError("Salesforce credentials required for salesforce mode")
        try:
            from simple_salesforce import Salesforce

            sf = Salesforce(
                username=self._settings.sf_username,
                password=self._settings.sf_password,
                security_token=self._settings.sf_security_token,
                domain=self._settings.sf_domain,
            )
            for obj in ("Opportunity", "Account"):
                desc = getattr(sf, obj).describe()
                fields = [f["name"] for f in desc["fields"][:8]]
                soql = f"SELECT {', '.join(fields)} FROM {obj} LIMIT 500"
                records = getattr(sf, obj).query(soql)["records"]
                rows = [{k: v for k, v in r.items() if k != "attributes"} for r in records]
                self._frames[obj] = pd.DataFrame(rows)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Salesforce load failed (%s); falling back to mock", exc)
            self._load_mock()

    def get_frame(self, object_name: str) -> pd.DataFrame:
        if object_name not in self._frames:
            if object_name in OBJECT_FRAMES:
                self._frames[object_name] = OBJECT_FRAMES[object_name]()
            else:
                return pd.DataFrame()
        return self._frames[object_name].copy()

    def all_frames(self) -> dict[str, pd.DataFrame]:
        return {k: v.copy() for k, v in self._frames.items()}


_ingest: CRMIngestService | None = None


def get_ingest_service() -> CRMIngestService:
    global _ingest
    if _ingest is None:
        _ingest = CRMIngestService()
        _ingest.load_all()
    return _ingest
