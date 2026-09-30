import React from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { FactBar } from "@/shared/ui";
import { formatDisplayDate } from "@/shared/lib/date-formatter";
import { useReportHeader } from "@/features/report/data/hooks";

interface ReportHeaderProps {
  slug: string;
}

export const ReportHeader: React.FC<ReportHeaderProps> = ({ slug }) => {
  const { data: header, isLoading } = useReportHeader(slug);

  if (isLoading || !header) {
    return (
      <div className="bg-white border-b border-slate-200 py-6 px-6 sm:px-8 mb-6 animate-pulse">
        <div className="h-4 w-32 bg-slate-200 rounded mb-2" />
        <div className="h-8 w-64 bg-slate-200 rounded mb-4" />
        <div className="h-14 w-full bg-slate-100 rounded-lg" />
      </div>
    );
  }

  const cover = header.cover || {};
  const companyName = header.name || cover.company_name || slug;
  const website = cover.website || header.cover?.website;
  const researchCutoff = cover.research_cutoff || header.asOfDate;
  const reportRef = cover.report_reference;

  const ribbonItems = (header.ribbon || []).filter(
    (item): item is [string, string] => Array.isArray(item) && item.length === 2
  );

  return (
    <div className="bg-white border-b border-slate-200 py-6 px-4 sm:px-8 mb-6 shadow-xs">
      <div className="max-w-(--content-max-width) mx-auto">
        {/* Overline Masthead */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Startup Screening Report
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              {header.audienceLabel || "Founder Screen"}
            </span>
          </div>

          {reportRef && (
            <span className="text-xs font-mono text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
              Ref: <strong className="text-slate-700 font-semibold">{reportRef}</strong>
            </span>
          )}
        </div>

        {/* Title and Website */}
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3 mb-3">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#1e2a3a]">
            {companyName}
          </h1>

          {website && (
            <a
              href={website.startsWith("http") ? website : `https://${website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-[#0369a1] hover:text-[#075985] bg-sky-50/70 hover:bg-sky-100/70 border border-sky-200 rounded-md transition-colors w-fit"
            >
              <span>{website.replace(/^https?:\/\//, "")}</span>
              <ExternalLink className="w-3.5 h-3.5 shrink-0" />
            </a>
          )}
        </div>

        {/* Metadata row */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1.5 text-xs text-slate-500 mb-5">
          {researchCutoff && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Research cut-off:</span>
              <span className="font-semibold text-slate-800 tabular-nums">
                {formatDisplayDate(researchCutoff)}
              </span>
            </div>
          )}
          {header.asOfDate && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Report date:</span>
              <span className="font-semibold text-slate-800 tabular-nums">
                {formatDisplayDate(header.asOfDate)}
              </span>
            </div>
          )}
        </div>

        {/* Compact Fact Bar Ribbon */}
        {ribbonItems.length > 0 && <FactBar items={ribbonItems} />}
      </div>
    </div>
  );
};
