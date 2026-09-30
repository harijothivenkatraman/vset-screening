from typing import Any

SUPPORTED_CANONICAL_VERSIONS = {"commercial-screen-canonical.2"}
SUPPORTED_SCHEMA_VERSIONS = {"vset.screen.v2"}


class VersionGateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def check_version_gate(raw_data: dict[str, Any]) -> None:
    canonical = raw_data.get("canonical")
    if not isinstance(canonical, dict):
        raise VersionGateError("Invalid format: missing root 'canonical' object")

    meta = canonical.get("meta")
    if not isinstance(meta, dict):
        raise VersionGateError("Invalid format: missing 'canonical.meta' object")

    canonical_version = meta.get("canonical_version")
    if not canonical_version:
        raise VersionGateError("Missing required 'canonical.meta.canonical_version'")

    if canonical_version not in SUPPORTED_CANONICAL_VERSIONS:
        raise VersionGateError(
            f"Unsupported canonical_version '{canonical_version}'. Supported: {sorted(SUPPORTED_CANONICAL_VERSIONS)}"
        )

    content = canonical.get("content")
    if not isinstance(content, dict):
        raise VersionGateError("Invalid format: missing 'canonical.content' object")

    final = content.get("final")
    if not isinstance(final, dict):
        raise VersionGateError("Invalid format: missing 'canonical.content.final' object")

    final_meta = final.get("meta")
    if not isinstance(final_meta, dict):
        raise VersionGateError("Invalid format: missing 'canonical.content.final.meta' object")

    schema_version = final_meta.get("schema_version")
    if not schema_version:
        raise VersionGateError("Missing required 'canonical.content.final.meta.schema_version'")

    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise VersionGateError(
            f"Unsupported schema_version '{schema_version}'. Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
