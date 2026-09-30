import copy

import pytest

from app.infrastructure.ingestion.version_gate import (
    VersionGateError,
    check_version_gate,
)


def test_version_gate_valid(terraspark_json):
    # Should not raise
    check_version_gate(terraspark_json)


def test_version_gate_invalid_canonical_version(terraspark_json):
    data = copy.deepcopy(terraspark_json)
    data["canonical"]["meta"]["canonical_version"] = "unsupported-version.9"
    with pytest.raises(VersionGateError, match="Unsupported canonical_version"):
        check_version_gate(data)


def test_version_gate_invalid_schema_version(terraspark_json):
    data = copy.deepcopy(terraspark_json)
    data["canonical"]["content"]["final"]["meta"]["schema_version"] = "vset.screen.v999"
    with pytest.raises(VersionGateError, match="Unsupported schema_version"):
        check_version_gate(data)


def test_version_gate_missing_canonical():
    with pytest.raises(VersionGateError, match="missing root 'canonical'"):
        check_version_gate({})
