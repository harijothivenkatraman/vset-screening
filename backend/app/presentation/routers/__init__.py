from app.presentation.routers.actions import router as actions_router
from app.presentation.routers.companies import router as companies_router
from app.presentation.routers.discovery import router as discovery_router
from app.presentation.routers.image_proxy import router as image_proxy_router
from app.presentation.routers.import_router import router as import_router
from app.presentation.routers.sections import router as sections_router
from app.presentation.routers.sources import router as sources_router

__all__ = [
    "companies_router",
    "sections_router",
    "actions_router",
    "sources_router",
    "import_router",
    "discovery_router",
    "image_proxy_router",
]
