import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Plus,
  KeyRound,
  ShieldCheck,
  Building2,
  Users,
  ArrowUpDown,
} from "lucide-react";
import { Avatar } from "@/shared/ui/Avatar";
import { Button } from "@/shared/ui/Button";
import { useFounders } from "../hooks";
import { FounderProfile, IdentityStatusType } from "../types";
import { AddProfileModal } from "./AddProfileModal";
import { AdminKeyModal, getAdminKey } from "./AdminKeyModal";

type TabFilter = "all" | "reference_screen" | "user_asserted" | "needs_evidence";
type SortOption = "recently_updated" | "name_asc";

export const FounderProfilesPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState<TabFilter>("all");
  const [sortOption, setSortOption] = useState<SortOption>("recently_updated");
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [hasAdminKey, setHasAdminKey] = useState<boolean>(() => Boolean(getAdminKey()));

  const { data, isLoading, error } = useFounders({
    search: searchTerm.trim() || undefined,
    page_size: 100,
  });

  const rawProfiles = useMemo(() => data?.items || [], [data]);

  // Tab counts
  const tabCounts = useMemo(() => {
    let allCount = rawProfiles.length;
    let refCount = 0;
    let manualCount = 0;
    let needsEvidenceCount = 0;

    rawProfiles.forEach((p) => {
      if (p.identity_status === "reference_screen") refCount++;
      else if (p.identity_status === "user_asserted") manualCount++;
      else if (p.identity_status === "unverified" || p.identity_status === "likely_match") needsEvidenceCount++;
    });

    return {
      all: allCount,
      reference_screen: refCount,
      user_asserted: manualCount,
      needs_evidence: needsEvidenceCount,
    };
  }, [rawProfiles]);

  // Filtered & sorted profiles
  const displayedProfiles = useMemo(() => {
    let result = rawProfiles.filter((p) => {
      if (activeTab === "reference_screen") return p.identity_status === "reference_screen";
      if (activeTab === "user_asserted") return p.identity_status === "user_asserted";
      if (activeTab === "needs_evidence") {
        return p.identity_status === "unverified" || p.identity_status === "likely_match";
      }
      return true;
    });

    if (sortOption === "name_asc") {
      result = [...result].sort((a, b) => a.founder_name.localeCompare(b.founder_name));
    } else {
      result = [...result].sort((a, b) => {
        const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
        const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
        return timeB - timeA;
      });
    }

    return result;
  }, [rawProfiles, activeTab, sortOption]);

  // Count unique companies
  const companiesCount = useMemo(() => {
    const set = new Set<string>();
    displayedProfiles.forEach((p) => {
      if (p.company_name) set.add(p.company_name.toLowerCase());
    });
    return set.size;
  }, [displayedProfiles]);

  const handleKeyChange = (active: boolean) => {
    setHasAdminKey(active);
  };

  const getShortChip = (status: IdentityStatusType) => {
    switch (status) {
      case "reference_screen":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-sky-50 text-sky-800 border border-sky-200">
            Screening report
          </span>
        );
      case "user_asserted":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            Manual
          </span>
        );
      case "unverified":
      case "likely_match":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
            Needs confirmation
          </span>
        );
      case "verified":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-800 border border-indigo-200">
            Verified match
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
            Profile
          </span>
        );
    }
  };

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return "";
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return isoStr.slice(0, 10);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20">
      {/* Header: Plain Title, One-line Description, Lock Control */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div>
            <h1 className="text-base font-bold tracking-tight text-slate-900">
              Founder Profiles
            </h1>
            <p className="text-[11px] text-slate-500">
              Verifiable founder profile extraction and catalog
            </p>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => setIsAdminModalOpen(true)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                hasAdminKey
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100"
                  : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200"
              }`}
              title={hasAdminKey ? "Editing unlocked" : "Unlock editing"}
              aria-label={hasAdminKey ? "Editing unlocked" : "Unlock editing"}
            >
              {hasAdminKey ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Editing unlocked</span>
                </>
              ) : (
                <>
                  <KeyRound className="w-3.5 h-3.5 text-slate-500" />
                  <span>Unlock editing</span>
                </>
              )}
            </button>

            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => {
                if (!hasAdminKey) {
                  setIsAdminModalOpen(true);
                } else {
                  setIsAddModalOpen(true);
                }
              }}
              className="gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Add Profile</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        {/* Search, Filter Tabs & Sort Toolbar */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by founder name or company..."
                className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-white"
              />
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-2 shrink-0">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={sortOption}
                onChange={(e) => setSortOption(e.target.value as SortOption)}
                aria-label="Sort founder profiles"
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-sky-500"
              >
                <option value="recently_updated">Recently updated</option>
                <option value="name_asc">Name (A-Z)</option>
              </select>
            </div>
          </div>

          {/* Filter Tabs with Counts */}
          <div className="flex items-center gap-1 border-b border-slate-200 overflow-x-auto pb-px">
            <button
              type="button"
              onClick={() => setActiveTab("all")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === "all"
                  ? "border-sky-600 text-sky-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              All ({tabCounts.all})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("reference_screen")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === "reference_screen"
                  ? "border-sky-600 text-sky-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              From screening reports ({tabCounts.reference_screen})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("user_asserted")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === "user_asserted"
                  ? "border-sky-600 text-sky-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              Added manually ({tabCounts.user_asserted})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("needs_evidence")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === "needs_evidence"
                  ? "border-sky-600 text-sky-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              Needs evidence ({tabCounts.needs_evidence})
            </button>
          </div>
        </div>

        {/* Clean Summary Line */}
        {!isLoading && !error && displayedProfiles.length > 0 && (
          <div className="text-xs text-slate-500 font-medium">
            Showing {displayedProfiles.length} {displayedProfiles.length === 1 ? "profile" : "profiles"} across{" "}
            {companiesCount} {companiesCount === 1 ? "company" : "companies"}
          </div>
        )}

        {/* Profiles List / Loading / Empty State */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white p-5 rounded-xl border border-slate-200 animate-pulse flex items-center gap-4"
              >
                <div className="w-10 h-10 rounded-full bg-slate-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-slate-200 rounded w-1/3" />
                  <div className="h-3 bg-slate-100 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 p-6 rounded-xl text-center text-xs text-rose-800">
            Failed to load founder profiles. Make sure the backend server is running.
          </div>
        ) : rawProfiles.length === 0 ? (
          /* Empty state: No profiles in catalog yet */
          <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-3">
            <Users className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-900">No founder profiles yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Get started by adding an online public profile or uploading a profile PDF.
            </p>
            <div className="pt-2">
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => {
                  if (!hasAdminKey) setIsAdminModalOpen(true);
                  else setIsAddModalOpen(true);
                }}
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Add your first founder profile
              </Button>
            </div>
          </div>
        ) : displayedProfiles.length === 0 ? (
          /* Empty state: Filter returns 0 */
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center space-y-2">
            <p className="text-xs text-slate-600 font-medium">No profiles match this filter</p>
            <p className="text-xs text-slate-400">
              Try choosing another tab or clearing your search query.
            </p>
            <div className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearchTerm("");
                  setActiveTab("all");
                }}
              >
                Clear filters
              </Button>
            </div>
          </div>
        ) : (
          /* Rows: entire row is a clickable link to profile */
          <div className="space-y-2.5">
            {displayedProfiles.map((profile) => (
              <Link
                key={profile.id}
                to={`/profiles/${profile.slug}`}
                className="group block bg-white rounded-xl border border-slate-200 p-4 shadow-xs hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5 min-w-0">
                    <Avatar name={profile.founder_name} size="md" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-bold text-slate-900 group-hover:text-sky-700 transition-colors truncate">
                          {profile.founder_name}
                        </span>
                        {getShortChip(profile.identity_status)}
                      </div>

                      <div className="text-xs text-slate-500 flex items-center gap-1.5 truncate mt-0.5">
                        {profile.headline ? (
                          <span className="truncate">{profile.headline}</span>
                        ) : profile.company_name ? (
                          <span>Founder at {profile.company_name}</span>
                        ) : (
                          <span>Founder</span>
                        )}
                        {profile.company_name && (
                          <>
                            <span>·</span>
                            <span className="inline-flex items-center gap-1 text-slate-600">
                              <Building2 className="w-3 h-3 text-slate-400" />
                              <span>{profile.company_name}</span>
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right side: Updated date */}
                  <div className="text-[11px] text-slate-400 shrink-0 text-right">
                    {formatDate(profile.updated_at || profile.created_at)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {/* Modals */}
      <AddProfileModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} />
      <AdminKeyModal
        isOpen={isAdminModalOpen}
        onClose={() => setIsAdminModalOpen(false)}
        onKeyChange={handleKeyChange}
      />
    </div>
  );
};
