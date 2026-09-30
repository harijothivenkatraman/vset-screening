import React from "react";
import { formatDisplayDate } from "@/shared/lib/date-formatter";
import { MutedValue } from "./MutedValue";

export interface TimelineEvent {
  date: string;
  event: string;
}

interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ events, className = "" }) => {
  if (!events || events.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Chronological Timeline"
      className={`relative pl-4 sm:pl-6 space-y-6 before:absolute before:left-2 sm:before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 ${className}`}
    >
      {events.map((item, idx) => (
        <div key={idx} className="relative flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-6 group">
          {/* Timeline node dot */}
          <div
            aria-hidden="true"
            className="absolute -left-4 sm:-left-6 mt-1.5 w-2.5 h-2.5 rounded-full bg-[#1e2a3a] ring-4 ring-white shadow-xs"
          />

          {/* Date column */}
          <div className="sm:w-32 shrink-0">
            <span className="inline-block text-xs font-semibold text-slate-700 tabular-nums px-2 py-0.5 rounded bg-slate-100 border border-slate-200/80">
              {formatDisplayDate(item.date)}
            </span>
          </div>

          {/* Event description */}
          <div className="flex-1 bg-white p-3.5 rounded-md border border-slate-200/80 shadow-2xs group-hover:border-slate-300 transition-colors">
            <p className="text-sm text-slate-800 leading-relaxed font-normal">
              <MutedValue value={item.event} />
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};
