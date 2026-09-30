import React from "react";
import { MutedValue } from "./MutedValue";

interface FactGridProps {
  items: [string, unknown][];
  columns?: 2 | 3;
  className?: string;
}

export const FactGrid: React.FC<FactGridProps> = ({
  items,
  columns = 3,
  className = "",
}) => {
  const colClass =
    columns === 3
      ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      : "grid-cols-1 sm:grid-cols-2";

  return (
    <div
      className={`grid ${colClass} gap-3 p-4 bg-white rounded-lg border border-slate-200 shadow-xs ${className}`}
    >
      {items.map(([key, val], idx) => (
        <div
          key={idx}
          className="flex flex-col space-y-1 p-2.5 rounded hover:bg-slate-50/70 transition-colors"
        >
          <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-500 leading-none">
            {key}
          </dt>
          <dd className="text-sm font-semibold text-slate-900 leading-snug break-words">
            <MutedValue value={val} />
          </dd>
        </div>
      ))}
    </div>
  );
};
