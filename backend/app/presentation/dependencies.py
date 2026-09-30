from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.action_item_repository import ActionItemRepository
from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.section_repository import SectionRepository
from app.application.ports.source_repository import SourceRepository
from app.application.services.get_actions import GetActionsService
from app.application.services.get_report_header import GetReportHeaderService
from app.application.services.get_section import GetSectionService
from app.application.services.get_section_nav import GetSectionNavService
from app.application.services.get_sources import GetSourcesService
from app.application.services.list_companies import ListCompaniesService
from app.infrastructure.ingestion.import_service import ReportImportService
from app.infrastructure.persistence.action_item_repo import SqlAlchemyActionItemRepository
from app.infrastructure.persistence.company_repo import SqlAlchemyCompanyRepository
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.persistence.report_repo import SqlAlchemyReportRepository
from app.infrastructure.persistence.section_repo import SqlAlchemySectionRepository
from app.infrastructure.persistence.source_repo import SqlAlchemySourceRepository


def get_company_repository(session: AsyncSession = Depends(get_db_session)) -> CompanyRepository:
    return SqlAlchemyCompanyRepository(session)


def get_report_repository(session: AsyncSession = Depends(get_db_session)) -> ReportRepository:
    return SqlAlchemyReportRepository(session)


def get_section_repository(session: AsyncSession = Depends(get_db_session)) -> SectionRepository:
    return SqlAlchemySectionRepository(session)


def get_action_item_repository(session: AsyncSession = Depends(get_db_session)) -> ActionItemRepository:
    return SqlAlchemyActionItemRepository(session)


def get_source_repository(session: AsyncSession = Depends(get_db_session)) -> SourceRepository:
    return SqlAlchemySourceRepository(session)


def get_list_companies_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
) -> ListCompaniesService:
    return ListCompaniesService(company_repo, report_repo)


def get_report_header_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
) -> GetReportHeaderService:
    return GetReportHeaderService(company_repo, report_repo)


def get_section_nav_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
) -> GetSectionNavService:
    return GetSectionNavService(company_repo, report_repo, section_repo)


def get_section_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    action_item_repo: ActionItemRepository = Depends(get_action_item_repository),
) -> GetSectionService:
    return GetSectionService(company_repo, report_repo, section_repo, action_item_repo)


def get_actions_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    action_item_repo: ActionItemRepository = Depends(get_action_item_repository),
) -> GetActionsService:
    return GetActionsService(company_repo, report_repo, action_item_repo)


def get_sources_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
) -> GetSourcesService:
    return GetSourcesService(company_repo, report_repo, source_repo)


def get_import_service(session: AsyncSession = Depends(get_db_session)) -> ReportImportService:
    return ReportImportService(session)
