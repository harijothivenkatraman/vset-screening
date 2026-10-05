"""Presentation API router for standalone Founder Profiles."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse

from app.application.services.pdf_extractor import MAX_PDF_BYTES
from app.application.use_cases.add_from_evidence import AddFromEvidenceUseCase
from app.application.use_cases.auto_discover_founder import AutoDiscoverFounderUseCase
from app.application.use_cases.delete_profile import DeleteProfileUseCase
from app.application.use_cases.export_profile import ExportProfileUseCase
from app.application.use_cases.get_profile import GetProfileUseCase
from app.application.use_cases.list_profiles import ListProfilesUseCase
from app.application.use_cases.restore_profile_version import RestoreProfileVersionUseCase
from app.application.use_cases.save_pending_profile import SavePendingProfileUseCase
from app.application.use_cases.try_public_fetch import TryPublicFetchUseCase
from app.application.use_cases.update_profile import UpdateProfileUseCase
from app.domain.entities.founder_profile import FounderProfile
from app.domain.exceptions import (
    DuplicateProfileException,
    InvalidEvidenceException,
    NoPreviousVersionException,
    ProfileNotFoundException,
)
from app.presentation.dependencies import (
    get_add_from_evidence_use_case,
    get_auto_discover_founder_use_case,
    get_delete_profile_use_case,
    get_export_profile_use_case,
    get_get_profile_use_case,
    get_list_profiles_use_case,
    get_restore_profile_version_use_case,
    get_save_pending_profile_use_case,
    get_try_public_fetch_use_case,
    get_update_profile_use_case,
)
from app.presentation.guards.api_key_guard import verify_admin_key, verify_read_or_admin_key
from app.presentation.guards.rate_limiter_guard import rate_limit_founder_action
from app.presentation.schemas.founder_schemas import (
    AddFounderProfileRequest,
    AutoDiscoverRequest,
    AutoDiscoverResponse,
    FounderProfileListResponse,
    FounderProfileResponse,
    SavePendingProfileRequest,
    TryPublicFetchRequest,
    TryPublicFetchResponse,
    UpdateFounderProfileRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/founders", tags=["founder-profiles"])


def _to_response_schema(profile: FounderProfile) -> FounderProfileResponse:
    data = profile.to_dict()
    return FounderProfileResponse.model_validate(data)


@router.get(
    "",
    response_model=FounderProfileListResponse,
    dependencies=[Depends(verify_read_or_admin_key)],
    summary="List founder profiles",
)
async def list_founder_profiles(
    search: str | None = Query(None, description="Search by name, company, or headline"),
    status: str | None = Query(None, description="Filter by identity status"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    use_case: ListProfilesUseCase = Depends(get_list_profiles_use_case),
) -> FounderProfileListResponse:
    result = await use_case.execute(
        search=search,
        status=status,
        limit=limit,
        offset=offset,
    )
    items = [_to_response_schema(p) for p in result.items]
    return FounderProfileListResponse(
        items=items,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.get(
    "/{id_or_slug}",
    response_model=FounderProfileResponse,
    dependencies=[Depends(verify_read_or_admin_key)],
    summary="Get single founder profile by UUID or slug",
)
async def get_founder_profile(
    id_or_slug: str,
    use_case: GetProfileUseCase = Depends(get_get_profile_use_case),
) -> FounderProfileResponse:
    try:
        profile = await use_case.execute(id_or_slug)
        return _to_response_schema(profile)
    except ProfileNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=FounderProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
    summary="Add founder profile from text evidence",
)
async def add_founder_profile(
    payload: AddFounderProfileRequest,
    use_case: AddFromEvidenceUseCase = Depends(get_add_from_evidence_use_case),
) -> Any:
    try:
        profile = await use_case.execute(
            founder_name=payload.founder_name,
            company_name=payload.company_name,
            notes=payload.notes,
            text=payload.evidence_text,
            allow_duplicate=payload.allow_duplicate,
        )
        return _to_response_schema(profile)
    except DuplicateProfileException as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": str(exc),
                "existing_id": exc.existing_id,
                "existing_slug": exc.existing_slug,
                "founder_name": exc.founder_name,
                "company_name": exc.company_name,
            },
        )
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/upload-pdf",
    response_model=FounderProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key), Depends(rate_limit_founder_action)],
    summary="Add founder profile from uploaded PDF file",
)
async def add_founder_profile_pdf(
    file: UploadFile = File(..., description="LinkedIn 'Save to PDF' export"),
    founder_name: str = Form(..., description="Founder name"),
    company_name: str | None = Form(None, description="Company name"),
    notes: str | None = Form(None, description="Internal notes"),
    allow_duplicate: bool = Form(False, description="Override duplicate warning"),
    use_case: AddFromEvidenceUseCase = Depends(get_add_from_evidence_use_case),
) -> Any:
    try:
        # Enforce 2 MB cap while streaming in chunks to reject early without buffering large files
        chunk_size = 64 * 1024
        chunks: list[bytes] = []
        total_bytes = 0
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_PDF_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"Uploaded PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB limit.",
                )
            chunks.append(chunk)
        pdf_bytes = b"".join(chunks)

        profile = await use_case.execute(
            founder_name=founder_name,
            company_name=company_name,
            notes=notes,
            pdf_bytes=pdf_bytes,
            pdf_filename=file.filename,
            allow_duplicate=allow_duplicate,
        )
        return _to_response_schema(profile)
    except DuplicateProfileException as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": str(exc),
                "existing_id": exc.existing_id,
                "existing_slug": exc.existing_slug,
                "founder_name": exc.founder_name,
                "company_name": exc.company_name,
            },
        )
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/fetch",
    response_model=TryPublicFetchResponse,
    dependencies=[Depends(verify_admin_key), Depends(rate_limit_founder_action)],
    summary="Try public fetch with bot detection and verification (never persists on failure)",
)
async def try_public_fetch(
    payload: TryPublicFetchRequest,
    use_case: TryPublicFetchUseCase = Depends(get_try_public_fetch_use_case),
) -> TryPublicFetchResponse:
    try:
        result = await use_case.execute(
            founder_name=payload.founder_name,
            linkedin_url=payload.linkedin_url,
            company_name=payload.company_name,
            save_as_pending=False,
        )
        return TryPublicFetchResponse(
            success=result.is_verified,
            message=result.message,
            status=result.diagnostic.outcome,
            profile=_to_response_schema(result.candidate) if result.candidate else None,
            verification_reason=result.candidate.retrieval.verification_reason if result.candidate else None,
        )
    except DuplicateProfileException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/auto-discover",
    response_model=AutoDiscoverResponse,
    dependencies=[Depends(verify_admin_key), Depends(rate_limit_founder_action)],
    summary="Auto-discover public profile across website and search fallback",
)
async def auto_discover_founder(
    payload: AutoDiscoverRequest,
    use_case: AutoDiscoverFounderUseCase = Depends(get_auto_discover_founder_use_case),
) -> AutoDiscoverResponse:
    try:
        result = await use_case.execute(
            founder_name=payload.founder_name,
            company_name=payload.company_name,
            profile_url=payload.profile_url,
            company_website=payload.company_website,
        )
        return AutoDiscoverResponse(
            outcome=result.outcome,
            candidate=_to_response_schema(result.candidate) if result.candidate else None,
            persisted=result.persisted,
            message=result.message,
            discovered_url=result.discovered_url,
        )
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/pending",
    response_model=FounderProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
    summary="Explicitly save a founder profile as pending evidence",
)
async def save_pending_founder_profile(
    payload: SavePendingProfileRequest,
    use_case: SavePendingProfileUseCase = Depends(get_save_pending_profile_use_case),
) -> Any:
    try:
        profile = await use_case.execute(
            founder_name=payload.founder_name,
            company_name=payload.company_name,
            linkedin_url=payload.linkedin_url,
            notes=payload.notes,
            verification_reason=payload.verification_reason,
            allow_duplicate=payload.allow_duplicate,
        )
        return _to_response_schema(profile)
    except DuplicateProfileException as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": str(exc),
                "existing_id": exc.existing_id,
                "existing_slug": exc.existing_slug,
                "founder_name": exc.founder_name,
                "company_name": exc.company_name,
            },
        )
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.put(
    "/{id_or_slug}",
    response_model=FounderProfileResponse,
    dependencies=[Depends(verify_admin_key)],
    summary="Update profile with new text/notes (creates restorable snapshot)",
)
async def update_founder_profile(
    id_or_slug: str,
    payload: UpdateFounderProfileRequest,
    use_case: UpdateProfileUseCase = Depends(get_update_profile_use_case),
) -> FounderProfileResponse:
    try:
        profile = await use_case.execute(
            identifier=id_or_slug,
            notes=payload.notes,
            text=payload.evidence_text,
            screening_assessment=payload.screening_assessment,
            is_user_override=True,
        )
        return _to_response_schema(profile)
    except ProfileNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/{id_or_slug}/restore",
    response_model=FounderProfileResponse,
    dependencies=[Depends(verify_admin_key)],
    summary="Restore profile to single previous version snapshot",
)
async def restore_founder_profile_version(
    id_or_slug: str,
    use_case: RestoreProfileVersionUseCase = Depends(get_restore_profile_version_use_case),
) -> FounderProfileResponse:
    try:
        profile = await use_case.execute(id_or_slug)
        return _to_response_schema(profile)
    except ProfileNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NoPreviousVersionException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{id_or_slug}",
    dependencies=[Depends(verify_admin_key)],
    summary="Delete profile (guarded by confirmation slug)",
)
async def delete_founder_profile(
    id_or_slug: str,
    confirm: str = Query(..., description="Must match the profile slug to confirm deletion"),
    use_case: DeleteProfileUseCase = Depends(get_delete_profile_use_case),
) -> dict[str, Any]:
    try:
        success = await use_case.execute(identifier=id_or_slug, confirm=confirm)
        return {"deleted": success, "slug": confirm}
    except ProfileNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidEvidenceException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{id_or_slug}/export",
    dependencies=[Depends(verify_read_or_admin_key)],
    summary="Export sanitized canonical JSON document",
)
async def export_founder_profile(
    id_or_slug: str,
    use_case: ExportProfileUseCase = Depends(get_export_profile_use_case),
) -> dict[str, Any]:
    try:
        return await use_case.execute(id_or_slug)
    except ProfileNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
