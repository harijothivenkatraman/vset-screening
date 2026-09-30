import React from "react";
import { Avatar } from "./Avatar";
import { MutedValue } from "./MutedValue";
import { Lightbulb } from "lucide-react";

export interface FounderData {
  name: string;
  role: string;
  lines: [string, string][];
  fit?: string;
}

interface FounderCardProps {
  founder: FounderData;
  className?: string;
}

export const FounderCard: React.FC<FounderCardProps> = ({
  founder,
  className = "",
}) => {
  return (
    <div
      className={`bg-white rounded-lg border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-colors flex flex-col justify-between ${className}`}
    >
      <div>
        {/* Header with Avatar and Role */}
        <div className="flex items-start gap-3.5 pb-3.5 mb-3.5 border-b border-slate-100">
          <Avatar name={founder.name} size="md" />
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-bold text-slate-900 truncate">
              {founder.name}
            </h3>
            <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium text-slate-600 bg-slate-100 rounded border border-slate-200/80">
              {founder.role}
            </span>
          </div>
        </div>

        {/* Lines (Education, Experience, Roles) */}
        {founder.lines && founder.lines.length > 0 && (
          <dl className="space-y-3 mb-4">
            {founder.lines.map(([label, val], idx) => (
              <div key={idx} className="space-y-0.5">
                <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  {label}
                </dt>
                <dd className="text-xs text-slate-800 leading-relaxed font-normal">
                  <MutedValue value={val} />
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {/* Founder-Market Fit Panel */}
      {founder.fit && (
        <div className="mt-2 pt-3 border-t border-slate-100 bg-[#f8fafc] p-3.5 rounded-md border-l-3 border-l-[#0369a1]">
          <div className="flex items-center gap-1.5 mb-1 text-[#0369a1]">
            <Lightbulb className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <h4 className="text-[11px] font-bold uppercase tracking-wider">
              Founder–Market Fit
            </h4>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed font-normal pl-5">
            {founder.fit}
          </p>
        </div>
      )}
    </div>
  );
};
