import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  FileText,
  HelpCircle,
  Info,
  CheckSquare,
  ChevronsDown,
  ChevronsUp,
} from "lucide-react";
import { useActions } from "@/features/report/data/hooks";
import {
  Badge,
  Button,
  Collapsible,
  EmptyState,
  ErrorState,
  ReportSkeleton,
} from "@/shared/ui";

export const ActionsPage: React.FC = () => {
  const { slug = "terraspark" } = useParams<{ slug: string }>();
  const { data, isLoading, isError, error, refetch } = useActions(slug);

  const [openTopics, setOpenTopics] = useState<Record<string, boolean>>({});

  // Ensure first topic is open by default when data loads
  useEffect(() => {
    if (data?.questions && data.questions.length > 0) {
      setOpenTopics((prev) => {
        if (Object.keys(prev).length === 0) {
          return { [data.questions[0].topic]: true };
        }
        return prev;
      });
    }
  }, [data?.questions]);

  if (isLoading) {
    return <ReportSkeleton />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load investor questions and requirements"
        message={error?.message || "Unable to retrieve actions data."}
        onRetry={() => refetch()}
      />
    );
  }

  const { presentation, questions, documents } = data;

  const allTopics = questions ? questions.map((q) => q.topic) : [];
  const allOpen =
    allTopics.length > 0 && allTopics.every((topic) => openTopics[topic]);

  const toggleAll = () => {
    if (allOpen) {
      setOpenTopics({});
    } else {
      const next: Record<string, boolean> = {};
      allTopics.forEach((t) => (next[t] = true));
      setOpenTopics(next);
    }
  };

  const toggleTopic = (topic: string) => {
    setOpenTopics((prev) => ({
      ...prev,
      [topic]: !prev[topic],
    }));
  };

  return (
    <article aria-labelledby="actions-title" className="space-y-8">
      {/* Tab Header */}
      <header className="border-b border-slate-200 pb-3">
        <h2
          id="actions-title"
          className="text-xl sm:text-2xl font-bold tracking-tight text-[#1e2a3a]"
        >
          {presentation?.actionSectionTitle || "Investor questions & information to prepare"}
        </h2>
      </header>

      {/* Concerns & Conflicts Banner (Neutral info style, exact wording, no green check) */}
      <section
        aria-labelledby="concerns-title"
        className="p-4 bg-slate-50 rounded-lg border border-slate-200/90 shadow-2xs"
      >
        <h3
          id="concerns-title"
          className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5"
        >
          Concerns & Conflicts
        </h3>
        <div className="flex items-center gap-2.5 text-xs text-slate-700 leading-relaxed font-normal">
          <Info className="w-4 h-4 text-slate-500 shrink-0" aria-hidden="true" />
          <span>No public concern or source conflict is recorded in this baseline.</span>
        </div>
      </section>

      {/* Intro paragraph */}
      {presentation?.actionIntro && (
        <p className="text-xs text-slate-600 leading-relaxed italic border-l-2 border-slate-300 pl-3">
          {presentation.actionIntro}
        </p>
      )}

      {/* Part A: Questions to prepare for */}
      <section aria-labelledby="part-a-title" className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200 gap-4">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-[#1e2a3a]" aria-hidden="true" />
            <h3
              id="part-a-title"
              className="text-base font-bold text-slate-900"
            >
              {presentation?.partATitle || "A. Questions to prepare for"}
            </h3>
          </div>

          {allTopics.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={toggleAll}
              className="text-xs font-medium text-slate-700 gap-1.5 py-1 px-2.5"
            >
              {allOpen ? (
                <>
                  <ChevronsUp className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Collapse all</span>
                </>
              ) : (
                <>
                  <ChevronsDown className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Expand all</span>
                </>
              )}
            </Button>
          )}
        </div>

        {questions && questions.length > 0 ? (
          <div className="space-y-3.5">
            {questions.map((topicGroup, tIdx) => {
              const isOpen = Boolean(openTopics[topicGroup.topic]);
              return (
                <Collapsible
                  key={tIdx}
                  id={`topic-${tIdx}`}
                  title={topicGroup.topic}
                  count={topicGroup.items.length}
                  isOpen={isOpen}
                  onToggle={() => toggleTopic(topicGroup.topic)}
                >
                  <div className="divide-y divide-slate-100 bg-white">
                    {topicGroup.items.map((item, qIdx) => (
                      <div
                        key={qIdx}
                        className="p-4 hover:bg-slate-50/60 transition-colors flex flex-col md:flex-row md:items-start gap-3.5"
                      >
                        <div className="shrink-0 md:w-14">
                          <Badge variant="outline" className="font-mono text-[11px] font-bold">
                            {item.id}
                          </Badge>
                        </div>
                        <div className="flex-1 space-y-1.5">
                          <p className="text-sm font-semibold text-slate-900 leading-relaxed">
                            {item.text}
                          </p>
                          {item.why && (
                            <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-md border border-slate-100 leading-relaxed font-normal">
                              <span className="font-semibold text-slate-700">
                                Why it matters:{" "}
                              </span>
                              {item.why}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </Collapsible>
              );
            })}
          </div>
        ) : (
          <EmptyState message="No due-diligence questions identified in this screen." />
        )}
      </section>

      {/* Part B: Supporting documents & data to prepare */}
      <section aria-labelledby="part-b-title" className="space-y-4 pt-4">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
          <FileText className="w-4 h-4 text-[#1e2a3a]" aria-hidden="true" />
          <h3
            id="part-b-title"
            className="text-base font-bold text-slate-900"
          >
            {presentation?.partBTitle || "B. Supporting documents & data to prepare"}
          </h3>
        </div>

        {documents && documents.length > 0 ? (
          <div className="grid grid-cols-1 gap-5">
            {documents.map((docGroup, gIdx) => (
              <div
                key={gIdx}
                className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs"
              >
                <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[#1e2a3a]">
                    {docGroup.group}
                  </h4>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-100 p-4 gap-4">
                  {/* Priority for initial review */}
                  <div>
                    <div className="flex items-center justify-between mb-3 pb-1.5 border-b border-slate-100">
                      <h5 className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                        Priority for Initial Review
                      </h5>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-sky-50 text-[#0369a1] border border-sky-200 tabular-nums">
                        {docGroup.priority.length} items
                      </span>
                    </div>
                    {docGroup.priority.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-slate-800 list-none pl-0">
                        {docGroup.priority.map((doc, dIdx) => (
                          <li
                            key={dIdx}
                            className="flex items-start gap-2.5 p-1.5 rounded hover:bg-slate-50 transition-colors"
                          >
                            <CheckSquare
                              className="w-3.5 h-3.5 text-[#0369a1] shrink-0 mt-0.5"
                              aria-hidden="true"
                            />
                            <span className="leading-relaxed font-normal">{doc}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-xs text-slate-400 italic">None listed</span>
                    )}
                  </div>

                  {/* Secondary follow-up */}
                  <div>
                    <div className="flex items-center justify-between mb-3 pb-1.5 border-b border-slate-100">
                      <h5 className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                        Follow-Up
                      </h5>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 tabular-nums">
                        {docGroup.secondary.length} items
                      </span>
                    </div>
                    {docGroup.secondary.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-slate-800 list-none pl-0">
                        {docGroup.secondary.map((doc, dIdx) => (
                          <li
                            key={dIdx}
                            className="flex items-start gap-2.5 p-1.5 rounded hover:bg-slate-50 transition-colors"
                          >
                            <CheckSquare
                              className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5"
                              aria-hidden="true"
                            />
                            <span className="leading-relaxed font-normal">{doc}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-xs text-slate-400 italic">None listed</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState message="No document requirements listed." />
        )}
      </section>
    </article>
  );
};
