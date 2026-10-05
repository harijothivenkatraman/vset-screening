import React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { getBlockRenderer } from "@/features/report/ui/blocks/registry";
import { useReportHeader, useSection, useSections } from "@/features/report/data/hooks";
import { EmptyState, ErrorState, ReportSkeleton } from "@/shared/ui";
import { OnThisPage, slugifyTitle } from "@/features/report/ui/shell/OnThisPage";

import { AtAGlanceStrip } from "@/features/report/ui/sections/AtAGlanceStrip";

export const SectionPage: React.FC = () => {
  const { slug = "terraspark", sectionKey = "company" } = useParams<{
    slug: string;
    sectionKey: string;
  }>();

  const {
    data: section,
    isLoading,
    isError,
    error,
    refetch,
  } = useSection(slug, sectionKey);

  const { data: header } = useReportHeader(slug);
  const { data: sectionsNav } = useSections(slug);

  if (isLoading) {
    return <ReportSkeleton />;
  }

  if (isError || !section) {
    return (
      <ErrorState
        title="Failed to load report section"
        message={error?.message || `Unable to retrieve section '${sectionKey}'.`}
        onRetry={() => refetch()}
      />
    );
  }

  const actionHeading =
    typeof header?.presentation?.section_action_heading === "string"
      ? header.presentation.section_action_heading
      : "Information to prepare";

  // Calculate Previous and Next links
  const currentIndex = sectionsNav?.findIndex((s) => s.key === sectionKey) ?? -1;
  const prevSection = currentIndex > 0 && sectionsNav ? sectionsNav[currentIndex - 1] : null;
  const nextSection =
    currentIndex >= 0 && sectionsNav && currentIndex < sectionsNav.length - 1
      ? sectionsNav[currentIndex + 1]
      : null;

  // Next fallback for tab 7 is Tab 8 (actions)
  const nextLink = nextSection
    ? { path: `/companies/${slug}/${nextSection.key}`, label: nextSection.title }
    : currentIndex === (sectionsNav?.length ?? 7) - 1
    ? { path: `/companies/${slug}/actions`, label: "Investor questions & information to prepare" }
    : null;

  const prevLink = prevSection
    ? { path: `/companies/${slug}/${prevSection.key}`, label: prevSection.title }
    : null;

  return (
    <div className="flex items-start gap-8">
      {/* Main Content Column */}
      <article aria-labelledby="section-title" className="flex-1 min-w-0 space-y-6">
        {/* Section Header */}
        <header className="border-b border-slate-200 pb-4 mb-6 space-y-3">
          <h2
            id="section-title"
            className="text-xl sm:text-2xl font-bold tracking-tight text-[#1e2a3a]"
          >
            {section.title}
          </h2>
          <AtAGlanceStrip sectionKey={sectionKey} blocks={section.blocks} />
        </header>

        {/* Render Data-Driven Blocks */}
        {section.blocks && section.blocks.length > 0 ? (
          <div className="space-y-6">
            {section.blocks.map((blockRaw, idx) => {
              if (!Array.isArray(blockRaw) || blockRaw.length < 2) {
                return null;
              }
              const block = blockRaw as [string, string, ...unknown[]];
              const [type, title] = block;

              // Avoid duplicate Founding Team card in team section since AtAGlanceStrip already displays it
              if ((sectionKey === "team" || sectionKey === "2") && type === "kv") {
                const items = Array.isArray(block[2]) ? (block[2] as [string, unknown][]) : [];
                const isOnlyFoundingTeam = items.length > 0 && items.every(([k]) => /founding\s*team/i.test(k));
                if (isOnlyFoundingTeam) {
                  return null;
                }
              }

              const Renderer = getBlockRenderer(type);
              const anchorId = slugifyTitle(String(title || `block-${idx}`), idx);

              return (
                <div key={idx} id={anchorId} className="scroll-mt-24">
                  <Renderer block={block} />
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState message="No content blocks recorded in this section." />
        )}

        {/* Section-level "Information to prepare" (SECTION_REQUEST items) */}
        {section.informationToPrepare && section.informationToPrepare.length > 0 && (
          <section
            aria-labelledby="section-actions-heading"
            className="mt-10 pt-6 border-t border-slate-200"
          >
            <div className="bg-slate-50/80 rounded-lg border border-slate-200 p-5 space-y-3">
              <h3
                id="section-actions-heading"
                className="text-[11px] font-bold uppercase tracking-wider text-[#1e2a3a] flex items-center gap-2"
              >
                <span>{actionHeading}</span>
              </h3>

              <ol className="space-y-2 list-none pl-0 text-sm">
                {section.informationToPrepare.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 text-slate-800">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-200 text-slate-700 text-[11px] font-bold shrink-0 mt-0.5 tabular-nums">
                      {idx + 1}
                    </span>
                    <div className="space-y-0.5 flex-1">
                      <p className="leading-relaxed font-normal">{item.text}</p>
                      {item.why && (
                        <p className="text-xs text-slate-500 italic">{item.why}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </section>
        )}

        {/* Previous / Next Section Pagination Navigation */}
        <nav
          aria-label="Section navigation links"
          className="pt-8 mt-10 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          {prevLink ? (
            <Link
              to={prevLink.path}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-md transition-colors shadow-2xs w-full sm:w-auto justify-center"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span className="truncate max-w-[200px]">Previous: {prevLink.label}</span>
            </Link>
          ) : (
            <div />
          )}

          {nextLink && (
            <Link
              to={nextLink.path}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-[#1e2a3a] hover:bg-[#2c3e56] rounded-md transition-colors shadow-2xs w-full sm:w-auto justify-center"
            >
              <span className="truncate max-w-[220px]">Next: {nextLink.label}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </nav>
      </article>

      {/* Right Rail Table of Contents (from 1440px / 2xl up) */}
      <OnThisPage blocks={section.blocks} />
    </div>
  );
};
