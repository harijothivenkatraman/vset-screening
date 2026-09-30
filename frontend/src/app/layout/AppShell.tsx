import React, { useState } from "react";
import { Outlet, useParams } from "react-router-dom";
import { ReportHeader } from "@/features/report/ui/shell/ReportHeader";
import { Sidebar } from "@/features/report/ui/shell/Sidebar";
import { TopBar } from "@/features/report/ui/shell/TopBar";

export const AppShell: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const currentSlug = slug || "terraspark";

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Bar */}
      <TopBar
        currentSlug={currentSlug}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
      />

      <div className="flex-1 flex">
        {/* Sidebar */}
        <Sidebar
          slug={currentSlug}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <main className="flex-1 md:pl-(--sidebar-width) flex flex-col min-w-0">
          {/* Report Cover / Header */}
          <ReportHeader slug={currentSlug} />

          {/* Tab Page Content */}
          <div className="flex-1 px-4 sm:px-8 pb-16 max-w-(--content-max-width) w-full mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
