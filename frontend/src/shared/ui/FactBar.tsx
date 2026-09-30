import React from "react";
import { MutedValue } from "./MutedValue";

interface FactBarProps {
  items: [string, string][];
  className?: string;
}

export const FactBar: React.FC<FactBarProps> = ({ items, className = "" }) => {
  if (!items || items.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Key Facts Summary"
      className={`bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden ${className}`}
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-slate-100">
        {items.map(([label, value], idx) => (
          <div
            key={idx}
            className="p-3.5 sm:p-4 flex flex-col justify-center space-y-1 hover:bg-slate-50/50 transition-colors"
          >
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 leading-none">
              {label}
            </span>
            <div className="text-sm font-semibold text-slate-900 tracking-tight leading-tight tabular-nums truncate">
              <MutedValue value={value} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
