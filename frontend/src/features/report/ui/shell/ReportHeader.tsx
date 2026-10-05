import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ExternalLink, RotateCw, AlertTriangle, X } from "lucide-react";
import { FactBar } from "@/shared/ui";
import { formatDisplayDate } from "@/shared/lib/date-formatter";
import { useReportHeader } from "@/features/report/data/hooks";

interface ReportHeaderProps {
  slug: string;
}

export const ReportHeader: React.FC<ReportHeaderProps> = ({ slug }) => {
  const navigate = useNavigate();
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
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

        {/* Metadata row with explicit Refresh control */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1.5 text-xs text-slate-500 mb-5">
          {researchCutoff && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Last updated:</span>
              <span className="font-semibold text-slate-800 tabular-nums">
                {formatDisplayDate(researchCutoff)}
              </span>
              <span className="text-slate-300">·</span>
              <button
                type="button"
                onClick={() => setShowConfirmModal(true)}
                className="inline-flex items-center gap-1 text-[#0369a1] hover:text-[#0284c7] font-semibold cursor-pointer underline decoration-dotted underline-offset-2"
                title="Initiate explicit refresh of company screening data"
              >
                <RotateCw className="w-3 h-3" />
                <span>Refresh</span>
              </button>
            </div>
          )}
          {header.asOfDate && !researchCutoff && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Report date:</span>
              <span className="font-semibold text-slate-800 tabular-nums">
                {formatDisplayDate(header.asOfDate)}
              </span>
              <span className="text-slate-300">·</span>
              <button
                type="button"
                onClick={() => setShowConfirmModal(true)}
                className="inline-flex items-center gap-1 text-[#0369a1] hover:text-[#0284c7] font-semibold cursor-pointer underline decoration-dotted underline-offset-2"
                title="Initiate explicit refresh of company screening data"
              >
                <RotateCw className="w-3 h-3" />
                <span>Refresh</span>
              </button>
            </div>
          )}
        </div>

        {/* Refresh Confirmation Modal */}
        {showConfirmModal && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="refresh-dialog-title"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150"
          >
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5 text-amber-700">
                  <div className="p-2 rounded-full bg-amber-50 border border-amber-200">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                  </div>
                  <h3 id="refresh-dialog-title" className="text-base font-bold text-slate-900">
                    Refresh screening data?
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowConfirmModal(false)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-md cursor-pointer"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Initiating a refresh will perform a new live discovery search for{" "}
                <strong className="text-slate-900 font-semibold">{companyName}</strong>, re-querying official sources and updating fact extractions. Existing manual evidence will be preserved.
              </p>

              <div className="pt-2 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowConfirmModal(false)}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-md transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowConfirmModal(false);
                    navigate(`/discover?company=${encodeURIComponent(slug)}`);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-[#0369a1] hover:bg-[#0284c7] rounded-md transition-colors shadow-2xs cursor-pointer"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>Confirm &amp; Refresh</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Compact Fact Bar Ribbon */}
        {ribbonItems.length > 0 && <FactBar items={ribbonItems} />}
      </div>
    </div>
  );
};
