import React from "react";
import { MutedValue } from "./MutedValue";

interface KeyValueGridProps {
  items: [string, unknown][];
  columns?: 1 | 2;
  className?: string;
}

export const KeyValueGrid: React.FC<KeyValueGridProps> = ({
  items,
  columns = 2,
  className = "",
}) => {
  const colClass = columns === 2 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1";

  return (
    <div
      className={`grid ${colClass} gap-x-8 gap-y-3 py-2 text-sm bg-white rounded border border-slate-200 p-4 ${className}`}
    >
      {items.map(([key, val], idx) => (
        <div
          key={idx}
          className="flex flex-col sm:flex-row sm:justify-between py-1 border-b border-slate-100 last:border-b-0"
        >
          <dt className="text-slate-500 font-medium text-xs uppercase tracking-wider min-w-[140px] pr-2">
            {key}
          </dt>
          <dd className="text-slate-900 font-normal sm:text-right text-sm">
            <MutedValue value={val} />
          </dd>
        </div>
      ))}
    </div>
  );
};
