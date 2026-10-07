import json
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.persistence.database import Base, get_db_session
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.domain.entities.discovery import CompanyProfile, PersonProfile, SourceDiagnostic
from app.presentation.dependencies import get_profile_scraper_port


class FakeProfileScraper(ProfileScraperPort):
    async def fetch_person(self, url: str) -> PersonProfile | None:
        return PersonProfile(
            name="Asha Example",
            headline="CEO at Example Corp",
            location="Bengaluru, Karnataka, India",
            summary="Founder and CEO building next-gen platforms.",
            experience=[
                {
                    "title": "CEO",
                    "company": "Example Corp",
                    "start": "2022",
                    "end": "Present",
                    "is_current": True,
                }
            ],
            education=[
                {"school": "Indian Institute of Science", "degree": "B.Tech", "year": "2018"}
            ],
            skills=["Leadership", "Strategy"],
        )

    async def fetch_company(self, url: str) -> CompanyProfile | None:
        return CompanyProfile(
            name="Example Corp",
            description="Enterprise platform provider.",
            industry="Software",
        )


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_profile_scraper_port] = lambda: FakeProfileScraper()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def terraspark_json() -> dict[str, Any]:
    candidates = [
        Path("F:/dev/Vset/reference/terraspark_founder_screen.json"),
        Path(__file__).parent.parent.parent / "reference" / "terraspark_founder_screen.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("terraspark_founder_screen.json not found")


@pytest.fixture
def mysa_json() -> dict[str, Any]:
    candidates = [
        Path("F:/dev/Vset/reference/mysa_founder_screen.json"),
        Path(__file__).parent.parent.parent / "reference" / "mysa_founder_screen.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("mysa_founder_screen.json not found")
