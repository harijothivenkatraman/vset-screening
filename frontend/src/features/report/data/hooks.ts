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
    queryFn: async () => {
      const section = await fetchSection(slug, key);
      
      // Merge founder_profiles into team tab if requested
      if (key === "team") {
        try {
          const founderSection = await fetchSection(slug, "founder_profiles");
          if (founderSection && founderSection.blocks) {
            
            // Extract website cards
            const cardsBlockIndex = section.blocks.findIndex((b: any) => Array.isArray(b) && b[0] === "cards");
            const websiteCards = cardsBlockIndex >= 0 ? ((section.blocks[cardsBlockIndex] as any)[2] as any[]) : [];
            
            // Remove cards block from team section to prevent duplicates
            if (cardsBlockIndex >= 0) {
              section.blocks.splice(cardsBlockIndex, 1);
            }

            // Track which website cards have been merged
            const mergedCardNames = new Set<string>();

            const modifiedFounderBlocks = founderSection.blocks.map((b: any) => {
              if (Array.isArray(b) && b[0] === "founder_profile") {
                 const payload = b[2] as any;
                 const name = payload.founder_name || String(b[1]).replace(/^Founder profile:\s*/i, "");
                 
                 const websiteCard = websiteCards.find((c: any) => c.name?.toLowerCase() === name.toLowerCase());
                 if (websiteCard) {
                   mergedCardNames.add(websiteCard.name?.toLowerCase());
                   return ["founder_profile", b[1], { ...payload, website_data: websiteCard }];
                 }
              }
              return b;
            });

            // For website cards that didn't have a LinkedIn profile, create a founder_profile block
            const unmergedCards = websiteCards.filter((c: any) => !mergedCardNames.has(c.name?.toLowerCase()));
            const newFounderBlocks = unmergedCards.map((c: any) => [
              "founder_profile",
              `Founder profile: ${c.name}`,
              {
                founder_name: c.name,
                retrieval: { status: "not_requested", source_type: "website" },
                website_data: c
              }
            ]);

            section.blocks = [...section.blocks, ...newFounderBlocks, ...modifiedFounderBlocks];

            // Merge information to prepare if it exists
            if (founderSection.informationToPrepare) {
              section.informationToPrepare = [
                ...(section.informationToPrepare || []),
                ...founderSection.informationToPrepare
              ];
            }
          }
        } catch (error) {
          // It's okay if founder_profiles doesn't exist
        }
      }
      
      return section;
    },
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
