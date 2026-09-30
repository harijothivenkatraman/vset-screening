import React from "react";
import { Menu, X } from "lucide-react";
import { CompanySwitcher } from "@/features/companies/CompanySwitcher";
import { useReportHeader } from "@/features/report/data/hooks";

interface TopBarProps {
  currentSlug: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentSlug,
  isSidebarOpen,
  onToggleSidebar,
}) => {
  const { data: header } = useReportHeader(currentSlug);

  return (
    <header className="h-(--topbar-height) bg-white border-b border-slate-200 sticky top-0 z-30 px-4 sm:px-6 flex items-center justify-between shadow-2xs">
      <div className="flex items-center gap-4 sm:gap-6">
        {/* Mobile toggle */}
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label={isSidebarOpen ? "Close menu" : "Open menu"}
          className="md:hidden p-1.5 rounded text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors cursor-pointer"
        >
          {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        {/* Brand / Logo */}
        <div className="flex items-baseline gap-2">
          <span className="font-extrabold tracking-tight text-xl text-[#1e2a3a]">
            vSET
          </span>
          <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 hidden sm:inline">
            Startup Screening
          </span>
        </div>

        <div className="h-4 w-px bg-slate-200 hidden sm:block" />

        {/* Company Switcher */}
        <CompanySwitcher currentSlug={currentSlug} />
      </div>

      {/* Right meta */}
      <div className="flex items-center gap-3">
        {header?.audienceLabel && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 hidden sm:inline-block">
            {header.audienceLabel}
          </span>
        )}
      </div>
    </header>
  );
};
