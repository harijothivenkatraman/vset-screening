import { useQuery } from "@tanstack/react-query";
import {
  fetchActions,
  fetchReportHeader,
  fetchSection,
  fetchSections,
  fetchSources,
} from "@/features/report/data/api";
import {
  ActionsData,
  ReportHeader,
  SectionDetail,
  SectionNavItem,
  SourcesData,
} from "@/features/report/domain/types";

export function useReportHeader(slug: string) {
  return useQuery<ReportHeader, Error>({
    queryKey: ["report-header", slug],
    queryFn: () => fetchReportHeader(slug),
    enabled: Boolean(slug),
  });
}

export function useSections(slug: string) {
  return useQuery<SectionNavItem[], Error>({
    queryKey: ["sections", slug],
    queryFn: () => fetchSections(slug),
    enabled: Boolean(slug),
  });
}

export function useSection(slug: string, key: string) {
  return useQuery<SectionDetail, Error>({
    queryKey: ["section", slug, key],
    queryFn: () => fetchSection(slug, key),
    enabled: Boolean(slug && key),
  });
}

export function useActions(slug: string) {
  return useQuery<ActionsData, Error>({
    queryKey: ["actions", slug],
    queryFn: () => fetchActions(slug),
    enabled: Boolean(slug),
  });
}

export function useSources(slug: string) {
  return useQuery<SourcesData, Error>({
    queryKey: ["sources", slug],
    queryFn: () => fetchSources(slug),
    enabled: Boolean(slug),
  });
}
