import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Plus,
  KeyRound,
  ShieldCheck,
  UserCheck,
  Building2,
  FileCheck2,
  Clock,
  ExternalLink,
  Users,
  Sparkles,
} from "lucide-react";
import { Avatar } from "@/shared/ui/Avatar";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { useFounders } from "../hooks";
import { FounderProfile, IdentityStatusType } from "../types";
import { AddProfileModal } from "./AddProfileModal";
import { AdminKeyModal, getAdminKey } from "./AdminKeyModal";

export const FounderProfilesPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [hasAdminKey, setHasAdminKey] = useState<boolean>(() => Boolean(getAdminKey()));

  const { data, isLoading, error } = useFounders({
    search: searchTerm.trim() || undefined,
    status: selectedStatus !== "all" ? selectedStatus : undefined,
    page_size: 100,
  });

  const profiles = useMemo(() => data?.items || [], [data]);

  // Aggregate stats
  const stats = useMemo(() => {
    let refCount = 0;
    let userCount = 0;
    let pendingCount = 0;

    profiles.forEach((p) => {
      if (p.identity_status === "reference_screen") refCount++;
      else if (p.identity_status === "user_asserted") userCount++;
      else if (p.identity_status === "unverified") pendingCount++;
    });

    return {
      total: data?.total ?? profiles.length,
      refCount,
      userCount,
      pendingCount,
    };
  }, [profiles, data?.total]);

  const handleKeyChange = (active: boolean) => {
    setHasAdminKey(active);
  };

  const getStatusBadge = (status: IdentityStatusType, sourceLabel: string) => {
    switch (status) {
      case "reference_screen":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-sky-50 text-sky-800 border border-sky-200">
            {sourceLabel || "Reference Screen"}
          </span>
        );
      case "user_asserted":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            {sourceLabel || "Provided by user (unverified)"}
          </span>
        );
      case "unverified":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
            {sourceLabel || "Pending evidence"}
          </span>
        );
      case "verified":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-800 border border-indigo-200">
            Verified Match
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
            {sourceLabel || "Unknown"}
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20">
      {/* Top Application Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-navy flex items-center justify-center text-white font-bold text-sm shadow-xs">
              FP
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-slate-900">
                  Founder Profiles
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  Standalone
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block">
                Verifiable founder profile extraction &amp; dossier catalog
              </p>
            </div>
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
              title="Toggle Admin Mode with API key"
            >
              {hasAdminKey ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="hidden sm:inline">Admin Mode</span>
                </>
              ) : (
                <>
                  <KeyRound className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">Read-Only</span>
                </>
              )}
            </button>

            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => setIsAddModalOpen(true)}
              className="gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Add Profile</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
        {/* Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-xs font-medium uppercase tracking-wider">Total Profiles</span>
              <Users className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-slate-900 tabular-nums">{stats.total}</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-xs font-medium uppercase tracking-wider">Reference Screens</span>
              <FileCheck2 className="w-4 h-4 text-sky-600" />
            </div>
            <div className="text-2xl font-bold text-sky-700 tabular-nums">{stats.refCount}</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-xs font-medium uppercase tracking-wider">User Asserted</span>
              <UserCheck className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-emerald-700 tabular-nums">{stats.userCount}</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-xs font-medium uppercase tracking-wider">Pending Evidence</span>
              <Clock className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-2xl font-bold text-amber-700 tabular-nums">{stats.pendingCount}</div>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="bg-white p-3 sm:p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          {/* Search bar */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by founder name, company, or skills..."
              className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-slate-50/50"
            />
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-1 border border-slate-200 p-1 rounded-lg bg-slate-50 overflow-x-auto">
            <button
              type="button"
              onClick={() => setSelectedStatus("all")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedStatus === "all"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setSelectedStatus("reference_screen")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedStatus === "reference_screen"
                  ? "bg-white text-sky-800 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Reference Screen
            </button>
            <button
              type="button"
              onClick={() => setSelectedStatus("user_asserted")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedStatus === "user_asserted"
                  ? "bg-white text-emerald-800 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              User Asserted
            </button>
            <button
              type="button"
              onClick={() => setSelectedStatus("unverified")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                selectedStatus === "unverified"
                  ? "bg-white text-amber-800 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Pending
            </button>
          </div>
        </div>

        {/* Profiles Grid / List */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white p-6 rounded-xl border border-slate-200 animate-pulse h-32" />
            ))}
          </div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 p-6 rounded-xl text-center text-xs text-rose-800">
            Failed to load founder profiles. Make sure the backend server is running.
          </div>
        ) : profiles.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-3">
            <Users className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-900">No founder profiles found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchTerm || selectedStatus !== "all"
                ? "Try clearing your search filters or status tab."
                : "Get started by adding manual evidence text or uploading a LinkedIn profile PDF."}
            </p>
            <div className="pt-2">
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => setIsAddModalOpen(true)}
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Add First Profile
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                {/* Left profile info */}
                <div className="flex items-start gap-4 flex-1 min-w-0">
                  <Avatar name={profile.founder_name} size="lg" />
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/profiles/${profile.slug}`}
                        className="text-base font-bold text-slate-900 hover:text-sky-700 transition-colors truncate"
                      >
                        {profile.founder_name}
                      </Link>
                      {profile.company_name && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          <Building2 className="w-3 h-3 text-slate-500" />
                          <span>{profile.company_name}</span>
                        </span>
                      )}
                      {getStatusBadge(profile.identity_status, profile.retrieval.source_label)}
                    </div>

                    {profile.headline && (
                      <p className="text-xs text-slate-600 line-clamp-1">{profile.headline}</p>
                    )}

                    {/* Stats line */}
                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 pt-1">
                      <span>{profile.experience_timeline.length} roles</span>
                      <span>·</span>
                      <span>{profile.education.length} education</span>
                      {profile.skills.length > 0 && (
                        <>
                          <span>·</span>
                          <span>{profile.skills.length} skills</span>
                        </>
                      )}
                      {profile.has_previous_version && (
                        <>
                          <span>·</span>
                          <span className="text-sky-700 font-medium">Snapshot available</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right actions */}
                <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                  <Link
                    to={`/profiles/${profile.slug}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 transition-colors"
                  >
                    <span>View Profile</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
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
