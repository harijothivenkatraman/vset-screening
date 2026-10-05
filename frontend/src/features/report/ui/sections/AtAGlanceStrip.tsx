import React from "react";
import { Users, DollarSign, Layers } from "lucide-react";

interface AtAGlanceStripProps {
  sectionKey?: string;
  blocks: unknown[];
  className?: string;
}

export const AtAGlanceStrip: React.FC<AtAGlanceStripProps> = ({
  sectionKey,
  blocks,
  className = "",
}) => {
  if (!blocks || blocks.length === 0) return null;

  const validBlocks = blocks.filter(
    (b): b is [string, string, ...unknown[]] => Array.isArray(b) && b.length >= 2
  );

  // --- 1. Team Tab (Section 2) ---
  if (sectionKey === "team" || sectionKey === "2") {
    // Look for Founding team KV item
    let foundingTeamText: string | null = null;
    let leadingInt: string | null = null;
    let otherExecsCount: number | null = null;
    let founderCount = 0;

    for (const b of validBlocks) {
      if (b[0] === "kv" && Array.isArray(b[2])) {
        for (const [key, val] of b[2] as [string, unknown][]) {
          if (/founding\s*team/i.test(key)) {
            foundingTeamText = String(val);
            const match = foundingTeamText.match(/^(\d+)/);
            if (match) {
              leadingInt = match[1];
            }
          }
        }
      }
      if (b[0] === "cards" && /founder/i.test(String(b[1] ?? "")) && Array.isArray(b[2])) {
        founderCount += (b[2] as unknown[]).length;
      }
      if (b[0] === "founder_profile") {
        founderCount += 1;
      }
      if (b[0] === "table" && Array.isArray(b[3])) {
        const title = String(b[1] ?? "");
        if (/management|executives/i.test(title)) {
          otherExecsCount = (b[3] as unknown[]).length;
        }
      }
    }

    if (!leadingInt && founderCount > 0) {
      leadingInt = String(founderCount);
      foundingTeamText = `${founderCount} member${founderCount === 1 ? "" : "s"}`;
    }

    if (!foundingTeamText && otherExecsCount === null) return null;

    return (
      <div
        className={`bg-slate-50/90 border border-slate-200 rounded-lg p-3.5 flex flex-col md:flex-row md:items-center gap-4 text-xs shadow-2xs ${className}`}
      >
        <div className="flex items-start gap-2.5 flex-1 min-w-0">
          <div className="p-1.5 rounded bg-white border border-slate-200 text-[#1e2a3a] shrink-0 mt-0.5">
            <Users className="w-4 h-4" aria-hidden="true" />
          </div>
          <div className="space-y-0.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
              Founding Team {leadingInt ? `(${leadingInt})` : ""}
            </span>
            <p className="text-slate-800 font-medium leading-relaxed">
              {foundingTeamText}
            </p>
          </div>
        </div>

        {otherExecsCount !== null && (
          <div className="flex items-start gap-2.5 md:border-l md:border-slate-200 md:pl-4 shrink-0">
            <div className="p-1.5 rounded bg-white border border-slate-200 text-slate-600 shrink-0 mt-0.5">
              <Layers className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Additional Management
              </span>
              <span className="text-slate-900 font-semibold tabular-nums">
                {otherExecsCount} {otherExecsCount === 1 ? "executive" : "executives"} recorded
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }

  // --- 2. Funding Tab (Section 7) ---
  if (sectionKey === "funding" || sectionKey === "7") {
    let fundingSentence: string | null = null;
    let roundCount = 0;

    for (const b of validBlocks) {
      if (b[0] === "para") {
        const text = typeof b[2] === "string" ? b[2] : String(b[2] || "");
        const sentences = text.split(/(?<=\.\s+)/);
        const totalsSentence = sentences.find((s) =>
          /reported financing totals/i.test(s)
        );

        if (totalsSentence) {
          fundingSentence = totalsSentence.trim();
        } else if (!fundingSentence && (/totals/i.test(text) || /completed/i.test(text))) {
          fundingSentence = sentences[0]?.trim() || null;
        }
      }
      if (b[0] === "table" && Array.isArray(b[3])) {
        roundCount = (b[3] as unknown[]).length;
      }
    }

    if (!fundingSentence && roundCount === 0) return null;

    return (
      <div
        className={`bg-slate-50/90 border border-slate-200 rounded-lg p-3.5 flex flex-col md:flex-row md:items-center gap-4 text-xs shadow-2xs ${className}`}
      >
        {fundingSentence && (
          <div className="flex items-start gap-2.5 flex-1 min-w-0">
            <div className="p-1.5 rounded bg-white border border-slate-200 text-[#0369a1] shrink-0 mt-0.5">
              <DollarSign className="w-4 h-4" aria-hidden="true" />
            </div>
            <div className="space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Reported Financing Baseline
              </span>
              <p className="text-slate-800 font-medium leading-relaxed">
                {fundingSentence}
              </p>
            </div>
          </div>
        )}

        {roundCount > 0 && (
          <div className="flex items-start gap-2.5 md:border-l md:border-slate-200 md:pl-4 shrink-0">
            <div className="p-1.5 rounded bg-white border border-slate-200 text-slate-600 shrink-0 mt-0.5">
              <Layers className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Financing Events
              </span>
              <span className="text-slate-900 font-semibold tabular-nums">
                {roundCount} {roundCount === 1 ? "round" : "events"} in timeline
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Hidden if absent for other sections
  return null;
};
