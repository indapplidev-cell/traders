from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from app.engine_orchestrator.pipeline_result import json_safe


class PublicState(Enum):
    RECOVERING = "RECOVERING"


@dataclass
class Envelope:
    state: PublicState
    values: object


def test_enum_top_level_uses_public_value_before_dunder_dict():
    assert hasattr(PublicState.RECOVERING, "__dict__")
    assert json_safe(PublicState.RECOVERING) == "RECOVERING"


def test_enum_nested_in_dataclass_mapping_and_sequences_uses_public_value():
    payload = Envelope(
        PublicState.RECOVERING,
        {
            "list": [PublicState.RECOVERING],
            "tuple": (PublicState.RECOVERING,),
            "set": {PublicState.RECOVERING},
        },
    )
    assert json_safe(payload) == {
        "state": "RECOVERING",
        "values": {
            "list": ["RECOVERING"],
            "tuple": ["RECOVERING"],
            "set": ["RECOVERING"],
        },
    }


def test_enum_private_fields_never_leak():
    encoded = repr(json_safe({"state": PublicState.RECOVERING}))
    assert "_value_" not in encoded
    assert "_name_" not in encoded


def test_datetime_and_decimal_serialization_is_unchanged():
    observed_at = datetime(2026, 7, 22, 12, 34, 56, tzinfo=timezone.utc)
    assert json_safe({"at": observed_at, "value": Decimal("1.2300")}) == {
        "at": "2026-07-22T12:34:56+00:00",
        "value": "1.2300",
    }
