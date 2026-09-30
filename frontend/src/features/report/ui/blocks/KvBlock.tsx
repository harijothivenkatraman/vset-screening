import React from "react";
import { FactGrid } from "@/shared/ui";

interface KvBlockProps {
  block: [string, string, ...unknown[]];
}

export const KvBlock: React.FC<KvBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const items = Array.isArray(payload) ? (payload as [string, unknown][]) : [];

  return (
    <div className="my-5 space-y-2">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}
      <FactGrid items={items} />
    </div>
  );
};
