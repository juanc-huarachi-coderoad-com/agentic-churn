"""Reads and parses the on-disk client profile YAML (spec §6.2) into
`ClientProfileInput` — Pydantic does the schema validation (REQ-M3-07); this module's
only job is the file read + YAML parse.
"""

from pathlib import Path

import yaml

from app.context.domain.profile_schema import ClientProfileInput


class ProfileFileNotFoundError(Exception):
    pass


def load_profile_yaml(path: str) -> ClientProfileInput:
    file_path = Path(path)
    if not file_path.is_file():
        raise ProfileFileNotFoundError(f"Client profile YAML not found at {path!r}")

    raw = yaml.safe_load(file_path.read_text())
    return ClientProfileInput.model_validate(raw)
