import { apiClient } from "@/core/http-client";
import {
  ActionsData,
  ReportHeader,
  SectionDetail,
  SectionNavItem,
  SourcesData,
} from "@/features/report/domain/types";

interface SectionsNavResponse {
  sections: SectionNavItem[];
}

export async function fetchReportHeader(slug: string): Promise<ReportHeader> {
  return apiClient<ReportHeader>(`/companies/${slug}`);
}

export async function fetchSections(slug: string): Promise<SectionNavItem[]> {
  const res = await apiClient<SectionsNavResponse>(`/companies/${slug}/sections`);
  return res.sections;
}

export async function fetchSection(slug: string, key: string): Promise<SectionDetail> {
  return apiClient<SectionDetail>(`/companies/${slug}/sections/${key}`);
}

export async function fetchActions(slug: string): Promise<ActionsData> {
  return apiClient<ActionsData>(`/companies/${slug}/actions`);
}

export async function fetchSources(slug: string): Promise<SourcesData> {
  return apiClient<SourcesData>(`/companies/${slug}/sources`);
}
