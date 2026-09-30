import React from "react";

interface ListProps {
  items: string[];
  className?: string;
}

export const NumberedList: React.FC<ListProps> = ({ items, className = "" }) => {
  return (
    <ol className={`space-y-2.5 list-none pl-0 text-sm text-slate-800 ${className}`}>
      {items.map((item, idx) => {
        const dashIdx = item.indexOf(" - ");
        const colonIdx = item.indexOf(": ");
        const splitIdx =
          dashIdx !== -1 && (colonIdx === -1 || dashIdx < colonIdx)
            ? dashIdx
            : colonIdx;

        let lead = "";
        let rest = item;
        let delim = "";
        if (splitIdx !== -1 && splitIdx <= 45) {
          lead = item.substring(0, splitIdx);
          delim = splitIdx === dashIdx ? " - " : ": ";
          rest = item.substring(splitIdx + delim.length);
        }

        return (
          <li key={idx} className="flex items-start gap-3">
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold shrink-0 mt-0.5 tabular-nums border border-slate-200/80">
              {idx + 1}
            </span>
            <div className="flex-1 leading-relaxed">
              {lead ? (
                <>
                  <span className="font-semibold text-slate-900">{lead}</span>
                  <span className="text-slate-500 font-normal">{delim}</span>
                  <span>{rest}</span>
                </>
              ) : (
                item
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
};

export const BulletList: React.FC<ListProps> = ({ items, className = "" }) => {
  return (
    <ul className={`space-y-2 list-none pl-0 text-sm text-slate-800 ${className}`}>
      {items.map((item, idx) => {
        const dashIdx = item.indexOf(" - ");
        const colonIdx = item.indexOf(": ");
        const splitIdx =
          dashIdx !== -1 && (colonIdx === -1 || dashIdx < colonIdx)
            ? dashIdx
            : colonIdx;

        let lead = "";
        let rest = item;
        let delim = "";
        if (splitIdx !== -1 && splitIdx <= 45) {
          lead = item.substring(0, splitIdx);
          delim = splitIdx === dashIdx ? " - " : ": ";
          rest = item.substring(splitIdx + delim.length);
        }

        return (
          <li key={idx} className="flex items-start gap-2.5 leading-relaxed">
            <span className="text-[#0369a1] select-none text-base leading-none mt-0.5 shrink-0">
              •
            </span>
            <span className="flex-1">
              {lead ? (
                <>
                  <span className="font-semibold text-slate-900">{lead}</span>
                  <span className="text-slate-500 font-normal">{delim}</span>
                  <span>{rest}</span>
                </>
              ) : (
                item
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
};
