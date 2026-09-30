import React from "react";
import { NavLink } from "react-router-dom";
import { HelpCircle, Info } from "lucide-react";
import { useSections } from "@/features/report/data/hooks";

interface SidebarProps {
  slug: string;
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ slug, isOpen, onClose }) => {
  const { data: sections, isLoading } = useSections(slug);

  const staticTabs = [
    {
      key: "actions",
      title: "Investor questions & information to prepare",
      shortTitle: (
        <span className="leading-snug">
          Investor questions &amp;
          <br />
          information to prepare
        </span>
      ),
      path: `/companies/${slug}/actions`,
      icon: HelpCircle,
      index: (sections?.length || 7) + 1,
    },
    {
      key: "sources",
      title: "About this screen & sources",
      shortTitle: "About this screen & sources",
      path: `/companies/${slug}/sources`,
      icon: Info,
      index: (sections?.length || 7) + 2,
    },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-slate-200 w-(--sidebar-width)">
      {/* Sections heading */}
      <div className="p-4 pb-2 border-b border-slate-100">
        <h2 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          Report Sections
        </h2>
      </div>

      {/* Nav list */}
      <nav aria-label="Report navigation" className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading && (
          <div className="p-2 space-y-2">
            {[1, 2, 3, 4, 5, 6, 7].map((i) => (
              <div key={i} className="h-9 bg-slate-100 rounded-md animate-pulse" />
            ))}
          </div>
        )}

        {/* Dynamic section tabs 1-7 */}
        {sections?.map((sec, idx) => (
          <NavLink
            key={sec.key}
            to={`/companies/${slug}/${sec.key}`}
            onClick={onClose}
            title={sec.title}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2.5 min-h-[40px] rounded-md text-xs font-semibold transition-all ${
                isActive
                  ? "bg-[#1e2a3a] text-white shadow-xs"
                  : "text-slate-700 hover:bg-slate-100 hover:text-slate-900 active:bg-slate-200"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`flex items-center justify-center w-5 h-5 rounded text-[11px] font-bold shrink-0 tabular-nums ${
                    isActive ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {idx + 1}
                </span>
                <span className="truncate leading-tight">{sec.title}</span>
              </>
            )}
          </NavLink>
        ))}

        {/* Divider with Group Heading */}
        <div className="pt-4 pb-1 px-3">
          <div className="border-t border-slate-200 mb-2" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Diligence &amp; Evidence
          </span>
        </div>

        {/* Tabs 8 & 9 */}
        {staticTabs.map((tab) => (
          <NavLink
            key={tab.key}
            to={tab.path}
            onClick={onClose}
            title={tab.title}
            className={({ isActive }) =>
              `flex items-start gap-2.5 px-3 py-2 min-h-[42px] rounded-md text-xs font-semibold transition-all ${
                isActive
                  ? "bg-[#1e2a3a] text-white shadow-xs"
                  : "text-slate-700 hover:bg-slate-100 hover:text-slate-900 active:bg-slate-200"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`flex items-center justify-center w-5 h-5 rounded text-[11px] font-bold shrink-0 mt-0.5 tabular-nums ${
                    isActive ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {tab.index}
                </span>
                <span className="leading-snug">{tab.shortTitle}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer info */}
      <div className="p-3 border-t border-slate-100 text-[11px] font-medium text-slate-500 text-center">
        vSET Commercial Screen
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop static sidebar */}
      <aside className="hidden md:block fixed left-0 top-(--topbar-height) bottom-0 z-20">
        {sidebarContent}
      </aside>

      {/* Mobile drawer with backdrop */}
      {isOpen && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
            onClick={onClose}
            aria-hidden="true"
          />
          <div className="relative z-50 flex h-full">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
