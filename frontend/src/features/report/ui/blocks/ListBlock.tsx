import React from "react";
import { BulletList } from "@/shared/ui";

interface ListBlockProps {
  block: [string, string, ...unknown[]];
}

export const ListBlock: React.FC<ListBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const items = Array.isArray(payload) ? (payload as string[]) : [];

  const isShortList =
    title?.toLowerCase().includes("target market") ||
    (items.length > 0 && items.every((it) => typeof it === "string" && it.length <= 40));

  return (
    <div className="my-5 space-y-2">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}

      {isShortList ? (
        <div className="flex flex-wrap gap-2 pt-0.5">
          {items.map((item, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-white text-slate-800 border border-slate-200/90 shadow-2xs hover:bg-slate-50 transition-colors"
            >
              {item}
            </span>
          ))}
        </div>
      ) : (
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
          <BulletList items={items} />
        </div>
      )}
    </div>
  );
};
