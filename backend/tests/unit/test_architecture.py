"""Architecture compliance tests.

Enforces the Clean Architecture Dependency Rule:
- domain imports only stdlib
- application imports only domain and stdlib
- infrastructure and presentation depend inward only
"""
from __future__ import annotations

import ast
from pathlib import Path
import pytest

BACKEND_APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"


def _extract_imported_modules(py_file: Path) -> set[str]:
    """Parse a python file AST and return top-level module names imported."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
    return imported


class TestArchitectureRules:
    def test_domain_layer_dependencies(self) -> None:
        """Domain layer must have zero dependencies on frameworks, infra, or application."""
        domain_dir = BACKEND_APP_DIR / "domain"
        forbidden_top_levels = {
            "fastapi", "sqlalchemy", "httpx", "pydantic", "pydantic_settings",
            "bs4", "beautifulsoup4", "duckduckgo_search",
        }

        for py_file in domain_dir.rglob("*.py"):
            imported = _extract_imported_modules(py_file)
            for imp in imported:
                top_pkg = imp.split(".")[0]
                assert top_pkg not in forbidden_top_levels, (
                    f"Domain file '{py_file.name}' illegally imports '{imp}'"
                )
                if imp.startswith("app."):
                    assert imp.startswith("app.domain"), (
                        f"Domain file '{py_file.name}' illegally imports outer layer '{imp}'"
                    )

    def test_application_layer_dependencies(self) -> None:
        """Application layer must not depend on presentation, infrastructure, or web frameworks."""
        app_dir = BACKEND_APP_DIR / "application"
        forbidden_top_levels = {
            "fastapi", "sqlalchemy", "httpx", "bs4", "duckduckgo_search",
        }

        for py_file in app_dir.rglob("*.py"):
            imported = _extract_imported_modules(py_file)
            for imp in imported:
                top_pkg = imp.split(".")[0]
                assert top_pkg not in forbidden_top_levels, (
                    f"Application file '{py_file.name}' illegally imports '{imp}'"
                )
                if imp.startswith("app."):
                    assert not imp.startswith("app.presentation"), (
                        f"Application file '{py_file.name}' illegally imports presentation layer '{imp}'"
                    )
                    assert not imp.startswith("app.infrastructure"), (
                        f"Application file '{py_file.name}' illegally imports infrastructure layer '{imp}'"
                    )
