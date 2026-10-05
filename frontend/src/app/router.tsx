import React from "react";
import { Navigate, createBrowserRouter, useParams } from "react-router-dom";
import { FounderProfilesPage, FounderProfileDetailPage } from "@/features/founders";

const LegacyCompanyRedirect: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  if (slug) {
    // If accessing legacy company route, try to redirect to profile with matching slug prefix
    return <Navigate to={`/profiles/${slug}`} replace />;
  }
  return <Navigate to="/" replace />;
};

export const router = createBrowserRouter([
  {
    path: "/",
    element: <FounderProfilesPage />,
  },
  {
    path: "/profiles/:slug",
    element: <FounderProfileDetailPage />,
  },
  {
    path: "/companies/:slug/founder_profiles",
    element: <LegacyCompanyRedirect />,
  },
  {
    path: "/companies/:slug/team",
    element: <LegacyCompanyRedirect />,
  },
  {
    path: "/companies/:slug/*",
    element: <LegacyCompanyRedirect />,
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
