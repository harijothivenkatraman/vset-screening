import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.ingestion.import_service import ReportImportService
from app.infrastructure.persistence.database import async_session_factory, init_db


def find_reference_files() -> list[Path]:
    search_dirs = [
        Path(os.environ["REFERENCE_DIR"]) if "REFERENCE_DIR" in os.environ else None,
        Path(__file__).parent / "reference",
        Path(__file__).parent.parent / "reference",
        Path.cwd() / "reference",
        Path("/app/reference"),
    ]

    files: list[Path] = []
    for d in search_dirs:
        if d and d.is_dir():
            t_file = d / "terraspark_founder_screen.json"
            m_file = d / "mysa_founder_screen.json"
            if t_file.exists() and t_file not in files:
                files.append(t_file)
            if m_file.exists() and m_file not in files:
                files.append(m_file)
        if len(files) >= 2:
            break
    return files


async def seed() -> list[tuple[str, str]]:
    print("=== Initializing Database Schema ===")
    await init_db()

    ref_files = find_reference_files()
    if not ref_files:
        print("[ERROR] No reference JSON files found in ./reference or parent directory!")
        sys.exit(1)

    print(f"Found {len(ref_files)} reference file(s) to import:")
    for f in ref_files:
        print(f" - {f}")

    results: list[tuple[str, str]] = []
    async with async_session_factory() as session:
        importer = ReportImportService(session)
        for f in ref_files:
            print(f"\nImporting '{f.name}'...")
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            result = await importer.import_report(data)
            print(f"Result: status='{result.status}', company='{result.company_slug}', message='{result.message}'")
            results.append((result.company_slug, result.status))

    print("\n=== Seeding Completed Successfully! ===")
    return results


if __name__ == "__main__":
    asyncio.run(seed())
