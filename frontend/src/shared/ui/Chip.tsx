import React from "react";

interface ChipProps {
  label: string;
  value: string;
  className?: string;
}

export const Chip: React.FC<ChipProps> = ({ label, value, className = "" }) => {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-200 bg-white text-xs shadow-xs ${className}`}
    >
      <span className="font-semibold uppercase tracking-wider text-slate-500 text-[10px]">
        {label}
      </span>
      <span className="text-slate-900 font-medium tabular-nums">{value}</span>
    </div>
  );
};
