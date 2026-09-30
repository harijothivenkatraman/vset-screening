import React from "react";
import { FounderCard } from "@/shared/ui";
import { FounderData } from "@/shared/ui/FounderCard";

interface CardsBlockProps {
  block: [string, string, ...unknown[]];
}

export const CardsBlock: React.FC<CardsBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const cards = Array.isArray(payload) ? (payload as FounderData[]) : [];

  const gridClass =
    cards.length <= 2
      ? "grid-cols-1 md:grid-cols-2"
      : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3";

  return (
    <div className="my-6 space-y-3">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}
      <div className={`grid ${gridClass} gap-4`}>
        {cards.map((c, idx) => (
          <FounderCard key={idx} founder={c} />
        ))}
      </div>
    </div>
  );
};
