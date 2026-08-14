"""SQLAlchemy implementation of ClientProfileRepositoryPort. Raw parameterized SQL,
matching the rest of the codebase's DDL-first pattern (no ORM declarative models).
"""

from datetime import time
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.application.ports import (
    ClientProfileRepositoryPort,
    CommitmentSummary,
    ProductAreaSummary,
    ProfileVersionSummary,
    StakeholderSummary,
)
from app.context.domain.profile_schema import (
    CRITICALITY_MULTIPLIERS,
    INFLUENCE_MULTIPLIERS,
    ClientProfileInput,
)


class SqlAlchemyClientProfileRepository(ClientProfileRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_new_version(
        self, profile: ClientProfileInput, *, authored_by_user_id: UUID
    ) -> ProfileVersionSummary:
        current = (
            await self._session.execute(
                text(
                    "SELECT id, version_number FROM client_profile_versions "
                    "WHERE is_current LIMIT 1"
                )
            )
        ).one_or_none()
        next_version = (current.version_number + 1) if current is not None else 1

        if current is not None:
            await self._session.execute(
                text("UPDATE client_profile_versions SET is_current = false WHERE id = :id"),
                {"id": current.id},
            )

        start_str, end_str = profile.communication.working_hours.split("-")
        working_hours_start = time.fromisoformat(start_str)
        working_hours_end = time.fromisoformat(end_str)
        profile_id = uuid4()
        await self._session.execute(
            text(
                "INSERT INTO client_profile_versions "
                "(id, version_number, client_name, renewal_date, contract_value_band, "
                "business_goals, working_hours_start, working_hours_end, timezone, "
                "languages, communication_norms, exclusions, authored_by_user_id, is_current) "
                "VALUES (:id, :version_number, :client_name, :renewal_date, "
                "(:contract_value_band)::contract_value_band, :business_goals, "
                ":working_hours_start, :working_hours_end, :timezone, :languages, "
                ":communication_norms, :exclusions, :authored_by_user_id, true)"
            ),
            {
                "id": profile_id,
                "version_number": next_version,
                "client_name": profile.client,
                "renewal_date": profile.renewal_date,
                "contract_value_band": profile.contract_value_band,
                "business_goals": profile.business_goals,
                "working_hours_start": working_hours_start,
                "working_hours_end": working_hours_end,
                "timezone": profile.communication.timezone,
                "languages": profile.communication.languages,
                "communication_norms": profile.communication.norms,
                "exclusions": profile.exclusions,
                "authored_by_user_id": authored_by_user_id,
            },
        )

        for stakeholder in profile.stakeholders:
            await self._session.execute(
                text(
                    "INSERT INTO stakeholders (id, profile_version_id, external_id, name, role, "
                    "influence, influence_multiplier, signs_renewal, identifiers) "
                    "VALUES (:id, :profile_version_id, :external_id, :name, :role, "
                    "(:influence)::influence_level, :multiplier, :signs_renewal, :identifiers)"
                ),
                {
                    "id": uuid4(),
                    "profile_version_id": profile_id,
                    "external_id": stakeholder.id,
                    "name": stakeholder.name,
                    "role": stakeholder.role,
                    "influence": stakeholder.influence,
                    "multiplier": INFLUENCE_MULTIPLIERS[stakeholder.influence],
                    "signs_renewal": stakeholder.signs_renewal,
                    "identifiers": stakeholder.identifiers,
                },
            )

        for area in profile.product_areas:
            await self._session.execute(
                text(
                    "INSERT INTO product_areas (id, profile_version_id, key, criticality, "
                    "criticality_multiplier) "
                    "VALUES (:id, :profile_version_id, :key, (:criticality)::criticality_level, "
                    ":multiplier)"
                ),
                {
                    "id": uuid4(),
                    "profile_version_id": profile_id,
                    "key": area.key,
                    "criticality": area.criticality,
                    "multiplier": CRITICALITY_MULTIPLIERS[area.criticality],
                },
            )

        for commitment in profile.commitments:
            await self._session.execute(
                text(
                    "INSERT INTO commitments (id, profile_version_id, type, priority, "
                    "threshold_business_hours, cadence) "
                    "VALUES (:id, :profile_version_id, (:type)::commitment_type, :priority, "
                    ":threshold, :cadence)"
                ),
                {
                    "id": uuid4(),
                    "profile_version_id": profile_id,
                    "type": commitment.type,
                    "priority": commitment.priority,
                    "threshold": commitment.threshold_business_hours,
                    "cadence": commitment.cadence,
                },
            )

        for entry in profile.history:
            await self._session.execute(
                text(
                    "INSERT INTO profile_history_entries "
                    "(id, profile_version_id, event_date, description) "
                    "VALUES (:id, :profile_version_id, :event_date, :description)"
                ),
                {
                    "id": uuid4(),
                    "profile_version_id": profile_id,
                    "event_date": entry.date,
                    "description": entry.event,
                },
            )

        await self._session.commit()

        return ProfileVersionSummary(
            version_number=next_version,
            client_name=profile.client,
            renewal_date=profile.renewal_date,
            contract_value_band=profile.contract_value_band,
            stakeholders=[
                StakeholderSummary(
                    name=s.name, role=s.role, influence=s.influence, signs_renewal=s.signs_renewal
                )
                for s in profile.stakeholders
            ],
            product_areas=[
                ProductAreaSummary(key=a.key, criticality=a.criticality)
                for a in profile.product_areas
            ],
            commitments=[
                CommitmentSummary(
                    type=c.type, threshold_business_hours=c.threshold_business_hours
                )
                for c in profile.commitments
            ],
        )

    async def get_current(self) -> ProfileVersionSummary | None:
        profile = (
            await self._session.execute(
                text(
                    "SELECT id, version_number, client_name, renewal_date, contract_value_band "
                    "FROM client_profile_versions WHERE is_current LIMIT 1"
                )
            )
        ).one_or_none()
        if profile is None:
            return None

        stakeholder_rows = (
            await self._session.execute(
                text(
                    "SELECT name, role, influence, signs_renewal FROM stakeholders "
                    "WHERE profile_version_id = :pv"
                ),
                {"pv": profile.id},
            )
        ).all()
        product_area_rows = (
            await self._session.execute(
                text("SELECT key, criticality FROM product_areas WHERE profile_version_id = :pv"),
                {"pv": profile.id},
            )
        ).all()
        commitment_rows = (
            await self._session.execute(
                text(
                    "SELECT type, threshold_business_hours FROM commitments "
                    "WHERE profile_version_id = :pv"
                ),
                {"pv": profile.id},
            )
        ).all()

        return ProfileVersionSummary(
            version_number=profile.version_number,
            client_name=profile.client_name,
            renewal_date=profile.renewal_date,
            contract_value_band=profile.contract_value_band,
            stakeholders=[
                StakeholderSummary(
                    name=r.name, role=r.role, influence=r.influence, signs_renewal=r.signs_renewal
                )
                for r in stakeholder_rows
            ],
            product_areas=[
                ProductAreaSummary(key=r.key, criticality=r.criticality)
                for r in product_area_rows
            ],
            commitments=[
                CommitmentSummary(
                    type=r.type,
                    threshold_business_hours=(
                        float(r.threshold_business_hours)
                        if r.threshold_business_hours is not None
                        else None
                    ),
                )
                for r in commitment_rows
            ],
        )
