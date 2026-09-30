import React from "react";
import { ChevronDown } from "lucide-react";

interface CollapsibleProps {
  id: string;
  title: string;
  count?: number;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  className?: string;
}

export const Collapsible: React.FC<CollapsibleProps> = ({
  id,
  title,
  count,
  isOpen,
  onToggle,
  children,
  className = "",
}) => {
  const contentId = `${id}-content`;
  const buttonId = `${id}-button`;

  return (
    <div
      className={`bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden transition-colors ${className}`}
    >
      <button
        id={buttonId}
        type="button"
        aria-expanded={isOpen}
        aria-controls={contentId}
        onClick={onToggle}
        className="w-full px-4 py-3 bg-slate-50/70 hover:bg-slate-100/80 text-left flex items-center justify-between gap-4 transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-900 truncate">
            {title}
          </span>
          {typeof count === "number" && (
            <span className="text-[11px] font-semibold text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200 tabular-nums">
              {count}
            </span>
          )}
        </div>
        <ChevronDown
          aria-hidden="true"
          className={`w-4 h-4 text-slate-500 shrink-0 transition-transform duration-200 ${
            isOpen ? "rotate-180 text-slate-800" : ""
          }`}
        />
      </button>

      {isOpen && (
        <div id={contentId} role="region" aria-labelledby={buttonId}>
          {children}
        </div>
      )}
    </div>
  );
};
