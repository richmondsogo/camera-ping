"""Validation parity tests between backend Pydantic schemas and shared vectors."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.schemas.camera import validate_ip_address, validate_text_field

SHARED_VECTORS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "shared"
    / "camera-validation-vectors.json"
)


def load_vectors() -> list[dict[str, Any]]:
    with open(SHARED_VECTORS_PATH, encoding="utf-8") as f:
        data = json.load(f)
        return cast(list[dict[str, Any]], data)


@pytest.mark.parametrize("vector", load_vectors())
def test_vector_parity_backend(vector: dict[str, Any]) -> None:
    field = vector["field"]
    user_input = vector["input"]
    expected = vector["expected"]
    expected_stored = vector["expected_stored"]
    expected_msg = vector["expected_message"]

    max_len = 500 if field == "description" else 100

    if field == "ip_address":
        if expected == "valid":
            result = validate_ip_address(user_input)
            assert result == expected_stored
        else:
            with pytest.raises(Exception) as exc_info:
                validate_ip_address(user_input)
            assert expected_msg in str(exc_info.value)
    else:
        if expected == "valid":
            result = validate_text_field(user_input, max_length=max_len)
            assert result == expected_stored
        else:
            with pytest.raises(Exception) as exc_info:
                validate_text_field(user_input, max_length=max_len)
            assert expected_msg in str(exc_info.value)
