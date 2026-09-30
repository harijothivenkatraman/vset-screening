from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.infrastructure.ingestion.import_service import ReportImportService
from app.infrastructure.ingestion.version_gate import VersionGateError
from app.presentation.dependencies import get_import_service
from app.presentation.guards.api_key_guard import verify_api_key
from app.presentation.schemas.import_schemas import ImportResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/import",
    response_model=ImportResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def import_report_endpoint(
    payload: dict[str, Any],
    service: ReportImportService = Depends(get_import_service),
) -> ImportResponse:
    try:
        result = await service.import_report(payload)
        return ImportResponse(
            status=result.status,
            company_slug=result.company_slug,
            message=result.message,
        )
    except VersionGateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during import: {e}",
        ) from e
