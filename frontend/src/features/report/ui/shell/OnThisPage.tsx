import React, { useEffect, useState } from "react";
import { ListFilter } from "lucide-react";

interface BlockItem {
  id: string;
  title: string;
}

interface OnThisPageProps {
  blocks?: unknown[];
}

export function slugifyTitle(title: string, index: number): string {
  if (!title) return `block-${index}`;
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || `block-${index}`
  );
}

export const OnThisPage: React.FC<OnThisPageProps> = ({ blocks = [] }) => {
  const [activeId, setActiveId] = useState<string>("");

  const items: BlockItem[] = blocks
    .map((b, idx) => {
      if (!Array.isArray(b) || b.length < 2) return null;
      const title = String(b[1] || "").trim();
      if (!title) return null;
      return {
        id: slugifyTitle(title, idx),
        title,
      };
    })
    .filter((b): b is BlockItem => Boolean(b));

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 140;
      for (let i = items.length - 1; i >= 0; i--) {
        const el = document.getElementById(items[i].id);
        if (el && el.offsetTop <= scrollPosition) {
          setActiveId(items[i].id);
          return;
        }
      }
      if (items.length > 0) setActiveId(items[0].id);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, [items]);

  if (items.length <= 1) return null;

  const scrollToBlock = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const yOffset = -90; // TopBar offset
      const y = el.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: "smooth" });
      setActiveId(id);
    }
  };

  return (
    <aside
      aria-label="Table of contents"
      className="hidden 2xl:block w-56 shrink-0 sticky top-24 self-start pl-6 text-xs text-slate-600 border-l border-slate-200"
    >
      <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] text-slate-500 mb-3">
        <ListFilter className="w-3.5 h-3.5 text-slate-400" />
        <span>On this page</span>
      </div>
      <ul className="space-y-1.5 list-none pl-0">
        {items.map((item) => {
          const isActive = item.id === activeId;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => scrollToBlock(item.id)}
                className={`text-left w-full truncate py-1 transition-colors cursor-pointer select-none ${
                  isActive
                    ? "font-bold text-[#1e2a3a] border-l-2 -ml-[25px] pl-[23px] border-[#1e2a3a]"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {item.title}
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
};
