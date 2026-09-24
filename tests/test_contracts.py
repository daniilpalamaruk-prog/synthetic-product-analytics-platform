import json
from pathlib import Path

from saasgen.contracts import load_contract, validate_record


def test_all_json_contracts_are_parseable():
    for path in Path("contracts").glob("*.schema.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["type"] == "object"


def test_user_contract_rejects_missing_pii_and_accepts_synthetic_values():
    contract = load_contract("users")
    record = {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "registration_at": "2025-01-01T00:00:00+00:00",
        "country": "US", "device_type": "web", "acquisition_channel": "organic",
        "name": "Synthetic User 0000001", "email": "synthetic@example.test",
        "phone": "+15550001", "ip_address": "192.0.2.1", "initial_plan": "free",
    }
    assert validate_record(record, contract) == []
    del record["email"]
    assert "email: required" in validate_record(record, contract)
