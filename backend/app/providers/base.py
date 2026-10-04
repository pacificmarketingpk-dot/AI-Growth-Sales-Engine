"""Interfaces for future integrations. Nothing here fakes a connection.

To add an integration, subclass the relevant interface, register it in REGISTRY,
and it will appear in Settings with a real status.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DiscoveryCriteria:
    country: str = ""
    industry: str = ""
    company_size: str = ""
    job_titles: list[str] | None = None
    business_type: str = ""
    keywords: str = ""
    min_score: int = 0
    limit: int = 50


class ProspectingSource(ABC):
    """A permitted data provider (e.g. a licensed B2B database). Must use official APIs."""
    key: str
    label: str

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    async def search(self, criteria: DiscoveryCriteria) -> list[dict]: ...


class MessagingChannel(ABC):
    """Outbound channel. LinkedIn must use an official, authorized API only."""
    key: str
    label: str

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    async def send(self, recipient: dict, message: str) -> dict: ...


class CRMConnector(ABC):
    key: str
    label: str

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    async def push_prospect(self, prospect: dict) -> str: ...


# Registry of known-but-not-yet-implemented integrations. Status is always reported honestly.
FUTURE_INTEGRATIONS = [
    {"provider": "linkedin", "label": "LinkedIn (official API)", "category": "Messaging",
     "note": "Requires an approved LinkedIn partner integration. Messages are copied and sent by you until then."},
    {"provider": "email_outbound", "label": "Email sending", "category": "Messaging",
     "note": "Not enabled in V1. Automated emails to prospects are not sent."},
    {"provider": "crm", "label": "CRM (HubSpot, Pipedrive, ...)", "category": "CRM",
     "note": "Connector interface ready. Use CSV export meanwhile."},
    {"provider": "enrichment", "label": "Data enrichment provider", "category": "Prospect source",
     "note": "Connect a licensed B2B data provider to enable Prospect Discovery."},
    {"provider": "web_research", "label": "Web research provider", "category": "Research",
     "note": "Homepage review is built in. Deeper research providers can be added."},
]

PROSPECTING_SOURCES: list[ProspectingSource] = []  # register real, permitted sources here
