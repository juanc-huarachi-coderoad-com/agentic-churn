"""The client profile's schema (REQ-M3-01, REQ-M3-07) — mirrors spec §6.2's YAML shape
exactly. Pydantic, not a hand-rolled validator: already a dependency (FastAPI), and its
structured field-path errors are exactly what FR-001's "specific validation error"
needs (research.md).
"""

import re
from datetime import date

from pydantic import BaseModel, field_validator

# Category -> multiplier value (REQ-M3-03). A small fixed table, not part of the
# client's own YAML — data-base/04-schema-context.md's Notes section: "the mapping
# from category -> default value is a small seed/config table maintained separately
# from client data so it can be tuned globally without touching every deployment's
# profile." Values match data-base/11-seed-data.sql's seeded rows exactly.
INFLUENCE_MULTIPLIERS = {"sponsor": 1.60, "daily_user": 1.20, "unknown": 0.80}
CRITICALITY_MULTIPLIERS = {"critical": 1.50, "standard": 1.00, "peripheral": 0.60}


class StakeholderInput(BaseModel):
    id: str
    name: str
    role: str | None = None
    influence: str
    signs_renewal: bool = False
    identifiers: list[str] = []

    @field_validator("influence")
    @classmethod
    def influence_is_known(cls, value: str) -> str:
        if value not in INFLUENCE_MULTIPLIERS:
            raise ValueError(f"influence must be one of {sorted(INFLUENCE_MULTIPLIERS)}")
        return value


class ProductAreaInput(BaseModel):
    key: str
    criticality: str

    @field_validator("criticality")
    @classmethod
    def criticality_is_known(cls, value: str) -> str:
        if value not in CRITICALITY_MULTIPLIERS:
            raise ValueError(f"criticality must be one of {sorted(CRITICALITY_MULTIPLIERS)}")
        return value


class CommitmentInput(BaseModel):
    type: str
    priority: str | None = None
    threshold_business_hours: float | None = None
    cadence: str | None = None


class CommunicationInput(BaseModel):
    working_hours: str  # "08:00-18:00"
    timezone: str
    languages: list[str] = []
    norms: str | None = None

    @field_validator("working_hours")
    @classmethod
    def working_hours_is_a_range(cls, value: str) -> str:
        if not re.fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", value):
            raise ValueError('working_hours must look like "08:00-18:00"')
        return value


class HistoryEntryInput(BaseModel):
    date: date
    event: str


class ClientProfileInput(BaseModel):
    client: str
    renewal_date: date
    contract_value_band: str
    business_goals: list[str] = []
    stakeholders: list[StakeholderInput]
    product_areas: list[ProductAreaInput] = []
    commitments: list[CommitmentInput] = []
    communication: CommunicationInput
    exclusions: list[str] = []
    history: list[HistoryEntryInput] = []

    @field_validator("contract_value_band")
    @classmethod
    def contract_value_band_is_known(cls, value: str) -> str:
        if value not in {"strategic", "standard", "smb"}:
            raise ValueError("contract_value_band must be one of strategic, standard, smb")
        return value

    @field_validator("stakeholders")
    @classmethod
    def at_least_one_signs_renewal(
        cls, value: list[StakeholderInput]
    ) -> list[StakeholderInput]:
        if not any(s.signs_renewal for s in value):
            raise ValueError("at least one stakeholder must have signs_renewal: true")
        return value
