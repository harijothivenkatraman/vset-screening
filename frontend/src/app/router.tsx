import React from "react";
import { Navigate, createBrowserRouter, useParams } from "react-router-dom";
import { AppShell } from "@/app/layout/AppShell";
import { ActionsPage } from "@/features/report/ui/actions/ActionsPage";
import { SectionPage } from "@/features/report/ui/sections/SectionPage";
import { SourcesPage } from "@/features/report/ui/sources/SourcesPage";
import { useCompanies } from "@/features/companies/hooks";

const IndexRedirect: React.FC = () => {
  const { data: companies, isLoading } = useCompanies();
  if (isLoading) return null;
  const firstSlug = companies && companies.length > 0 ? companies[0].slug : "terraspark";
  return <Navigate to={`/companies/${firstSlug}/company`} replace />;
};

const CompanyRedirect: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  return <Navigate to={`/companies/${slug || "terraspark"}/company`} replace />;
};

export const router = createBrowserRouter([
  {
    path: "/",
    element: <IndexRedirect />,
  },
  {
    path: "/companies/:slug",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <CompanyRedirect />,
      },
      {
        path: "actions",
        element: <ActionsPage />,
      },
      {
        path: "sources",
        element: <SourcesPage />,
      },
      {
        path: ":sectionKey",
        element: <SectionPage />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
