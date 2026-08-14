"""Ports the context application layer depends on — implemented by
app.context.adapters.*. Application depends on these, never on a concrete adapter
(constitution P8), enforced mechanically by `.importlinter`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.context.domain.profile_schema import ClientProfileInput


@dataclass(frozen=True)
class StakeholderSummary:
    name: str
    role: str | None
    influence: str
    signs_renewal: bool


@dataclass(frozen=True)
class ProductAreaSummary:
    key: str
    criticality: str


@dataclass(frozen=True)
class CommitmentSummary:
    type: str
    threshold_business_hours: float | None


@dataclass(frozen=True)
class ProfileVersionSummary:
    version_number: int
    client_name: str
    renewal_date: date
    contract_value_band: str
    stakeholders: list[StakeholderSummary]
    product_areas: list[ProductAreaSummary]
    commitments: list[CommitmentSummary]


class ClientProfileRepositoryPort(ABC):
    @abstractmethod
    async def insert_new_version(
        self, profile: ClientProfileInput, *, authored_by_user_id: UUID
    ) -> ProfileVersionSummary:
        """Inserts a new `client_profile_versions` row (+ stakeholders/product_areas/
        commitments/profile_history_entries), flips the prior current version's
        `is_current` to false in the same transaction (REQ-M3-02)."""
        ...

    @abstractmethod
    async def get_current(self) -> ProfileVersionSummary | None: ...
