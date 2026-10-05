import React, { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  History,
  Trash2,
  ExternalLink,
  MapPin,
  Building2,
  Briefcase,
  GraduationCap,
  Award,
  FileCheck2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  KeyRound,
  FileText,
} from "lucide-react";
import { Avatar } from "@/shared/ui/Avatar";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Collapsible } from "@/shared/ui/Collapsible";
import { useFounder, useRestoreVersion, useDeleteFounder } from "../hooks";
import { exportFounderJson } from "../api";
import { UpdateProfileModal } from "./UpdateProfileModal";
import { GuardedDeleteModal } from "./GuardedDeleteModal";
import { AdminKeyModal, getAdminKey } from "./AdminKeyModal";

export const FounderProfileDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [hasAdminKey, setHasAdminKey] = useState<boolean>(() => Boolean(getAdminKey()));
  const [isAboutExpanded, setIsAboutExpanded] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: profile, isLoading, error } = useFounder(slug);
  const restoreMutation = useRestoreVersion();
  const deleteMutation = useDeleteFounder();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="text-xs text-slate-500 animate-pulse">Loading founder profile...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 space-y-4">
        <div className="text-sm font-semibold text-slate-800">Founder profile not found</div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-sky-700 hover:underline"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to All Profiles</span>
        </Link>
      </div>
    );
  }

  // Handle Export Canonical JSON
  const handleExportJson = async () => {
    try {
      const data = await exportFounderJson(profile.slug);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${profile.slug}-canonical.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setActionError("Failed to export canonical JSON.");
    }
  };

  // Handle Restore Version
  const handleRestore = async () => {
    if (!window.confirm("Restore the previous snapshot version? The current version will be overwritten with the restored snapshot.")) {
      return;
    }
    setActionError(null);
    try {
      await restoreMutation.mutateAsync({ slug: profile.slug });
    } catch (err: unknown) {
      if (err instanceof Error) setActionError(err.message);
      else setActionError("Failed to restore previous version.");
    }
  };

  // Handle Delete Confirmation
  const handleDeleteConfirm = async () => {
    setActionError(null);
    try {
      await deleteMutation.mutateAsync({ slug: profile.slug, confirm: profile.slug });
      setIsDeleteModalOpen(false);
      navigate("/");
    } catch (err: unknown) {
      if (err instanceof Error) setActionError(err.message);
      else setActionError("Failed to delete profile.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-24">
      {/* Top Breadcrumb & Admin Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>All Profiles</span>
          </Link>

          <button
            type="button"
            onClick={() => setIsAdminModalOpen(true)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
              hasAdminKey
                ? "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100"
                : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200"
            }`}
          >
            {hasAdminKey ? (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Admin Unlocked</span>
              </>
            ) : (
              <>
                <KeyRound className="w-3.5 h-3.5 text-slate-500" />
                <span>Unlock Admin</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-8 space-y-6">
        {actionError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{actionError}</span>
          </div>
        )}

        {/* 1. Header Profile Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <Avatar name={profile.founder_name} size="lg" />
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                    {profile.founder_name}
                  </h1>
                  {profile.company_name && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                      <Building2 className="w-3.5 h-3.5 text-slate-500" />
                      <span>{profile.company_name}</span>
                    </span>
                  )}
                </div>

                {profile.headline && (
                  <p className="text-sm text-slate-700 font-medium">{profile.headline}</p>
                )}

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-0.5">
                  {profile.location && (
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" />
                      <span>{profile.location}</span>
                    </span>
                  )}
                  {profile.linkedin_url && (
                    <a
                      href={profile.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sky-700 hover:underline"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>LinkedIn Profile</span>
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Source Chip with Provenance */}
            <div className="self-start sm:self-auto flex flex-col items-start sm:items-end gap-1">
              <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200">
                {profile.retrieval.source_label}
              </span>
              <span className="text-[11px] text-slate-400">
                Slug: <code className="font-mono">{profile.slug}</code>
              </span>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleExportJson}
                className="gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </Button>
            </div>

            <div className="flex items-center gap-2">
              {profile.has_previous_version && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleRestore}
                  disabled={restoreMutation.isPending}
                  className="gap-1.5 border-amber-300 text-amber-900 bg-amber-50 hover:bg-amber-100"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-amber-700" />
                  <span>{restoreMutation.isPending ? "Restoring..." : "Restore Version"}</span>
                </Button>
              )}

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsUpdateModalOpen(true)}
                className="gap-1.5"
              >
                <History className="w-3.5 h-3.5" />
                <span>Update / Re-upload</span>
              </Button>

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsDeleteModalOpen(true)}
                className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </Button>
            </div>
          </div>
        </div>

        {/* 2. From vSET Screening Assessment Card */}
        {profile.screening_assessment && (
          <div className="bg-sky-50/70 border border-sky-200 rounded-xl p-5 shadow-xs space-y-2">
            <div className="flex items-center gap-2 text-sky-900 font-semibold text-xs uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-sky-600" />
              <span>From vSET screening</span>
            </div>
            <p className="text-xs text-slate-800 leading-relaxed font-normal whitespace-pre-wrap">
              {profile.screening_assessment}
            </p>
          </div>
        )}

        {/* 3. Summary / About Card */}
        {profile.about && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">About</h2>
            <div className="text-xs text-slate-800 leading-relaxed font-normal">
              {profile.about.length > 280 && !isAboutExpanded ? (
                <>
                  <p>{profile.about.slice(0, 280)}...</p>
                  <button
                    type="button"
                    onClick={() => setIsAboutExpanded(true)}
                    className="inline-flex items-center gap-1 text-sky-700 font-medium mt-2 hover:underline"
                  >
                    <span>Show more</span>
                    <ChevronDown className="w-3.5 h-3.5" />
                  </button>
                </>
              ) : (
                <>
                  <p className="whitespace-pre-wrap">{profile.about}</p>
                  {profile.about.length > 280 && (
                    <button
                      type="button"
                      onClick={() => setIsAboutExpanded(false)}
                      className="inline-flex items-center gap-1 text-sky-700 font-medium mt-2 hover:underline"
                    >
                      <span>Show less</span>
                      <ChevronUp className="w-3.5 h-3.5" />
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* 4. Experience Timeline Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-slate-500" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Experience Timeline ({profile.experience_timeline.length})
              </h2>
            </div>
          </div>

          {profile.experience_timeline.length === 0 ? (
            <p className="text-xs text-slate-400 italic">Sections not available</p>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              {profile.experience_timeline.map((exp, idx) => (
                <div key={idx} className="relative group">
                  {/* Dot on timeline */}
                  <div className="absolute -left-[23px] top-1.5 w-3 h-3 rounded-full bg-white border-2 border-sky-600" />
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold text-slate-900">{exp.title}</h3>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                      <span className="font-medium text-slate-800">{exp.company}</span>
                      {exp.duration && (
                        <>
                          <span>·</span>
                          <span className="text-slate-500">{exp.duration}</span>
                        </>
                      )}
                      {exp.location && (
                        <>
                          <span>·</span>
                          <span className="text-slate-500">{exp.location}</span>
                        </>
                      )}
                    </div>
                    {exp.description && (
                      <p className="text-xs text-slate-600 leading-relaxed pt-1 whitespace-pre-wrap">
                        {exp.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 5. Education Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-slate-500" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Education ({profile.education.length})
              </h2>
            </div>
          </div>

          {profile.education.length === 0 ? (
            <p className="text-xs text-slate-400 italic">Sections not available</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {profile.education.map((edu, idx) => (
                <div key={idx} className="py-3 first:pt-0 last:pb-0 space-y-0.5">
                  <h3 className="text-xs font-semibold text-slate-900">{edu.school}</h3>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    {edu.degree && <span>{edu.degree}</span>}
                    {edu.field_of_study && <span>{edu.field_of_study}</span>}
                    {edu.year && (
                      <>
                        <span>·</span>
                        <span className="text-slate-500 tabular-nums">{edu.year}</span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 6. Skills & Certifications Card */}
        {(profile.skills.length > 0 || profile.certifications.length > 0) && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
            {profile.skills.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Skills ({profile.skills.length})
                </h2>
                <div className="flex flex-wrap gap-1.5">
                  {profile.skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200/80"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {profile.certifications.length > 0 && (
              <div className="space-y-3 pt-4 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  <Award className="w-4 h-4 text-slate-500" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Certifications ({profile.certifications.length})
                  </h2>
                </div>
                <div className="divide-y divide-slate-100">
                  {profile.certifications.map((cert, idx) => (
                    <div key={idx} className="py-2.5 first:pt-0 last:pb-0">
                      <div className="text-xs font-semibold text-slate-900">{cert.name}</div>
                      <div className="text-xs text-slate-500">
                        {cert.authority} {cert.year && `· ${cert.year}`}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 7. Provenance & Audit Details Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <FileText className="w-4 h-4 text-slate-500" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Provenance &amp; Audit Trail
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Retrieval Status</span>
              <span className="font-semibold text-slate-800">{profile.retrieval.status}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Identity Status</span>
              <span className="font-semibold text-slate-800">{profile.identity_status}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Source Label</span>
              <span className="text-slate-800">{profile.retrieval.source_label}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Created At</span>
              <span className="text-slate-800 font-mono text-[11px]">{profile.created_at}</span>
            </div>
            {profile.notes && (
              <div className="sm:col-span-2">
                <span className="text-slate-400 block mb-0.5">Operator Notes</span>
                <span className="text-slate-800 whitespace-pre-wrap">{profile.notes}</span>
              </div>
            )}
            {profile.warnings && profile.warnings.length > 0 && (
              <div className="sm:col-span-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 space-y-1">
                <span className="font-semibold block">Audit Warnings</span>
                <ul className="list-disc pl-4 space-y-0.5">
                  {profile.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Modals */}
      <UpdateProfileModal
        isOpen={isUpdateModalOpen}
        onClose={() => setIsUpdateModalOpen(false)}
        profile={profile}
      />
      <GuardedDeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDeleteConfirm}
        slug={profile.slug}
        founderName={profile.founder_name}
        isLoading={deleteMutation.isPending}
      />
      <AdminKeyModal
        isOpen={isAdminModalOpen}
        onClose={() => setIsAdminModalOpen(false)}
        onKeyChange={(active) => setHasAdminKey(active)}
      />
    </div>
  );
};
