"""REQ-M3-07 — accept/reject cases: missing required field, zero `signs_renewal: true`
stakeholders."""

import pytest
from pydantic import ValidationError

from app.context.domain.profile_schema import ClientProfileInput

_VALID = {
    "client": "Meridian Logistics",
    "renewal_date": "2026-11-08",
    "contract_value_band": "strategic",
    "stakeholders": [
        {
            "id": "stk_ana",
            "name": "Ana Reyes",
            "role": "CTO",
            "influence": "sponsor",
            "signs_renewal": True,
            "identifiers": ["ana.reyes@meridian.com"],
        }
    ],
    "communication": {
        "working_hours": "08:00-18:00",
        "timezone": "America/Bogota",
        "languages": ["es", "en"],
    },
}


def test_valid_profile_parses():
    profile = ClientProfileInput.model_validate(_VALID)
    assert profile.client == "Meridian Logistics"
    assert profile.stakeholders[0].influence == "sponsor"


def test_missing_required_field_is_rejected():
    invalid = {k: v for k, v in _VALID.items() if k != "client"}
    with pytest.raises(ValidationError):
        ClientProfileInput.model_validate(invalid)


def test_zero_signs_renewal_stakeholders_is_rejected():
    invalid = dict(_VALID)
    invalid["stakeholders"] = [
        {**_VALID["stakeholders"][0], "signs_renewal": False},
    ]
    with pytest.raises(ValidationError):
        ClientProfileInput.model_validate(invalid)


def test_unknown_influence_category_is_rejected():
    invalid = dict(_VALID)
    invalid["stakeholders"] = [{**_VALID["stakeholders"][0], "influence": "vip"}]
    with pytest.raises(ValidationError):
        ClientProfileInput.model_validate(invalid)


def test_malformed_working_hours_is_rejected():
    invalid = dict(_VALID)
    invalid["communication"] = {**_VALID["communication"], "working_hours": "all day"}
    with pytest.raises(ValidationError):
        ClientProfileInput.model_validate(invalid)
