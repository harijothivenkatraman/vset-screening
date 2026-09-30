import React from "react";
import { useParams } from "react-router-dom";
import { Calendar, ExternalLink, Info, ShieldAlert } from "lucide-react";
import { useSources } from "@/features/report/data/hooks";
import { formatDisplayDate } from "@/shared/lib/date-formatter";
import { Badge, EmptyState, ErrorState, MutedValue, ReportSkeleton } from "@/shared/ui";

export const SourcesPage: React.FC = () => {
  const { slug = "terraspark" } = useParams<{ slug: string }>();
  const { data, isLoading, isError, error, refetch } = useSources(slug);

  if (isLoading) {
    return <ReportSkeleton />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load sources and methodology information"
        message={error?.message || "Unable to retrieve sources."}
        onRetry={() => refetch()}
      />
    );
  }

  const { aboutText, limitations, researchWindow, sources } = data;

  return (
    <article aria-labelledby="sources-title" className="space-y-8">
      {/* Tab Header */}
      <header className="border-b border-slate-200 pb-3">
        <h2
          id="sources-title"
          className="text-xl sm:text-2xl font-bold tracking-tight text-[#1e2a3a]"
        >
          About this screen & sources
        </h2>
      </header>

      {/* About this screen narrative & methodology */}
      <section
        aria-labelledby="about-section-heading"
        className="bg-white rounded-lg border border-slate-200 p-5 space-y-4 shadow-xs"
      >
        <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
          <Info className="w-4 h-4 text-[#1e2a3a]" aria-hidden="true" />
          <h3
            id="about-section-heading"
            className="text-xs font-bold uppercase tracking-wider text-slate-700"
          >
            About This Screen
          </h3>
        </div>

        <p className="text-sm text-slate-800 leading-relaxed font-normal max-w-3xl">
          {aboutText}
        </p>

        {/* Limitations */}
        {limitations && limitations.length > 0 && (
          <div className="pt-3 border-t border-slate-100 space-y-2 max-w-3xl">
            <h4 className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
              <span>Scope & Limitations</span>
            </h4>
            <ul className="space-y-1.5 list-none pl-0 text-xs text-slate-600">
              {limitations.map((lim, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-slate-400 select-none">•</span>
                  <span className="leading-relaxed font-normal">{lim}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Research Window */}
        {researchWindow && (researchWindow.from || researchWindow.to) && (
          <div className="pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-500">
            <Calendar className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
            <span>
              Research window:{" "}
              <strong className="text-slate-700 font-semibold tabular-nums">
                {formatDisplayDate(researchWindow.from)}
              </strong>{" "}
              –{" "}
              <strong className="text-slate-700 font-semibold tabular-nums">
                {formatDisplayDate(researchWindow.to)}
              </strong>
            </span>
          </div>
        )}
      </section>

      {/* Numbered Source Cards */}
      <section aria-labelledby="evidence-sources-heading" className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
          <h3
            id="evidence-sources-heading"
            className="text-xs font-bold uppercase tracking-wider text-slate-500"
          >
            Evidence Register — Reviewed Sources ({sources.length})
          </h3>
        </div>

        {sources && sources.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sources.map((src) => {
              const href =
                src.canonicalUrl ||
                (src.displayUrl ? `https://${src.displayUrl}` : undefined);

              return (
                <div
                  key={src.sourceId}
                  className="bg-white rounded-lg border border-slate-200 p-4 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors"
                >
                  <div className="space-y-2.5">
                    {/* Header: Badge, Publisher, Date */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 tabular-nums shrink-0">
                          S{src.position}
                        </span>
                        {src.publisher && (
                          <Badge
                            variant="outline"
                            className="text-[11px] truncate max-w-[180px]"
                          >
                            {src.publisher}
                          </Badge>
                        )}
                      </div>

                      {src.publishedDate ? (
                        <span className="text-xs text-slate-500 tabular-nums whitespace-nowrap">
                          {formatDisplayDate(src.publishedDate)}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 italic">Undated</span>
                      )}
                    </div>

                    {/* Source Title */}
                    <h4 className="text-sm font-semibold text-slate-900 leading-snug">
                      {src.title || src.publisher || "Untitled Source"}
                    </h4>
                  </div>

                  {/* Domain Link */}
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    {href ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#0369a1] hover:underline hover:text-[#0284c7] transition-colors break-all group"
                      >
                        <span className="truncate max-w-[280px]">
                          {src.displayUrl || href}
                        </span>
                        <ExternalLink
                          className="w-3.5 h-3.5 shrink-0 group-hover:translate-x-0.5 transition-transform"
                          aria-hidden="true"
                        />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-400">
                        <MutedValue value={src.displayUrl} />
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState message="No external evidence sources recorded in this register." />
        )}
      </section>
    </article>
  );
};
