import React from "react";
import { FounderCard } from "@/shared/ui";
import { FounderData } from "@/shared/ui/FounderCard";

interface CardsBlockProps {
  block: [string, string, ...unknown[]];
}

export const CardsBlock: React.FC<CardsBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const cards = Array.isArray(payload) ? (payload as FounderData[]) : [];

  return (
    <div className="my-6 space-y-3">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}
      <div className="flex flex-col space-y-4 w-full">
        {cards.map((c, idx) => (
          <FounderCard key={idx} founder={c} />
        ))}
      </div>
    </div>
  );
};
