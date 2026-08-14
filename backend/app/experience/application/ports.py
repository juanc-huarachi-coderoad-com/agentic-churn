from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientProfileRecord:
    client_name: str


class ClientProfileRepositoryPort(ABC):
    @abstractmethod
    async def get_current(self) -> ClientProfileRecord | None:
        """The current (is_current = true) client_profile_versions row, or None if the
        database has never been seeded — the `no_profile` state (contracts/
        dashboard.md, spec.md Edge Cases)."""
        ...
