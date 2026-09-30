import copy

import pytest

from app.infrastructure.ingestion.schema_validator import validate_raw_report_json


def test_schema_validator_valid(terraspark_json):
    result = validate_raw_report_json(terraspark_json)
    assert result.canonical.meta.company_name == "TerraSpark"


def test_schema_validator_missing_meta(terraspark_json):
    data = copy.deepcopy(terraspark_json)
    del data["canonical"]["meta"]
    with pytest.raises(ValueError, match="Schema validation error"):
        validate_raw_report_json(data)


def test_schema_validator_missing_sections(terraspark_json):
    data = copy.deepcopy(terraspark_json)
    del data["canonical"]["content"]["sections"]
    with pytest.raises(ValueError, match="Schema validation error"):
        validate_raw_report_json(data)
