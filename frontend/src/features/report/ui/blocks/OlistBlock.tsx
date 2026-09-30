import React from "react";
import { NumberedList } from "@/shared/ui";

interface OlistBlockProps {
  block: [string, string, ...unknown[]];
}

export const OlistBlock: React.FC<OlistBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const items = Array.isArray(payload) ? (payload as string[]) : [];

  const areAllVeryShort =
    items.length > 0 &&
    items.length <= 6 &&
    items.every((it) => typeof it === "string" && it.length <= 40);

  return (
    <div className="my-5 space-y-2">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}

      {areAllVeryShort ? (
        <div className="flex flex-wrap gap-2.5 pt-0.5">
          {items.map((item, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-slate-900 border border-slate-200/90 shadow-2xs hover:bg-slate-50 transition-colors"
            >
              <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold flex items-center justify-center border border-slate-200">
                {idx + 1}
              </span>
              {item}
            </span>
          ))}
        </div>
      ) : (
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
          <NumberedList items={items} />
        </div>
      )}
    </div>
  );
};
