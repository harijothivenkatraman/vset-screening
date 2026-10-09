import React, { useState, useEffect } from "react";
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
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  KeyRound,
  FileText,
  Copy,
  Check,
} from "lucide-react";
import { Avatar } from "@/shared/ui/Avatar";
import { Button } from "@/shared/ui/Button";
import { useFounder, useRestoreVersion, useDeleteFounder } from "../hooks";
import { exportFounderJson } from "../api";
import { UpdateProfileModal } from "./UpdateProfileModal";
import { GuardedDeleteModal } from "./GuardedDeleteModal";
import { AdminKeyModal, getAdminKey } from "./AdminKeyModal";

const parseCertification = (
  cert: unknown
): { name: string; authority?: string | null; year?: string | null } => {
  if (typeof cert === "string") {
    const trimmed = cert.trim();
    if (trimmed.includes(" - ")) {
      const parts = trimmed.split(" - ");
      const name = parts[0].trim();
      const authority = parts.slice(1).join(" - ").trim() || null;
      return {
        name,
        authority: authority && authority.toLowerCase() !== name.toLowerCase() ? authority : null,
      };
    }
    return { name: trimmed };
  }
  if (cert && typeof cert === "object") {
    const obj = cert as Record<string, unknown>;
    const name = String(obj.name || obj.title || "").trim();
    const rawAuth = obj.authority || obj.issuer || obj.issued_by || obj.issuedBy;
    const authority = rawAuth ? String(rawAuth).trim() : null;
    const rawYear = obj.year || obj.issued_at || obj.issuedAt;
    const year = rawYear ? String(rawYear).trim() : null;
    return {
      name,
      authority: authority && authority.toLowerCase() !== name.toLowerCase() ? authority : null,
      year,
    };
  }
  return { name: String(cert || "") };
};

export const FounderProfileDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [hasAdminKey, setHasAdminKey] = useState<boolean>(() => Boolean(getAdminKey()));
  const [isAboutExpanded, setIsAboutExpanded] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const { data: profile, isLoading, error } = useFounder(slug);
  const restoreMutation = useRestoreVersion();
  const deleteMutation = useDeleteFounder();

  // Toast auto-dismiss
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 3500);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
  };

  const handleKeyChange = (active: boolean) => {
    setHasAdminKey(active);
    showToast(active ? "Editing unlocked" : "Editing locked");
  };

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
      showToast("JSON exported successfully");
    } catch {
      setActionError("Failed to export canonical JSON.");
    }
  };

  // Handle Copy Profile Link
  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      showToast("Link copied to clipboard");
    } catch {
      showToast("Failed to copy link");
    }
  };

  // Handle Restore Version
  const handleRestore = async () => {
    if (!hasAdminKey) {
      setIsAdminModalOpen(true);
      return;
    }
    if (!window.confirm("Restore the previous snapshot version? The current version will be overwritten with the restored snapshot.")) {
      return;
    }
    setActionError(null);
    try {
      const adminKey = getAdminKey() || undefined;
      await restoreMutation.mutateAsync({ slug: profile.slug, apiKey: adminKey });
      showToast("Previous version restored");
    } catch (err: unknown) {
      if (err instanceof Error) setActionError(err.message);
      else setActionError("Failed to restore previous version.");
    }
  };

  // Handle Delete Confirmation
  const handleDeleteConfirm = async () => {
    setActionError(null);
    try {
      const adminKey = getAdminKey() || undefined;
      await deleteMutation.mutateAsync({ slug: profile.slug, confirm: profile.slug, apiKey: adminKey });
      setIsDeleteModalOpen(false);
      navigate("/");
    } catch (err: unknown) {
      if (err instanceof Error) setActionError(err.message);
      else setActionError("Failed to delete profile.");
    }
  };

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return "Unknown";
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

  const getHumanIdentityLabel = (status: string, reason?: string | null) => {
    switch (status) {
      case "verified":
        return reason || "Verified against company website";
      case "reference_screen":
        return "From vSET screening report";
      case "user_asserted":
        return "Provided by user (unverified)";
      case "likely_match":
      case "unverified":
        return "Needs confirmation (unverified candidate)";
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-24">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-4 py-2.5 rounded-lg shadow-lg text-xs flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2"
        >
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Breadcrumb & Lock Control Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>All Profiles</span>
          </Link>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyLink}
              className="p-1.5 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
              title="Copy profile link"
              aria-label="Copy profile link"
            >
              <Copy className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => setIsAdminModalOpen(true)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
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
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-6 space-y-6">
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
                      <span>Online Profile</span>
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Source Chip */}
            <div className="self-start sm:self-auto">
              <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200">
                {profile.retrieval.source_label}
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
                <div title={!hasAdminKey ? "Unlock editing to restore version" : ""}>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleRestore}
                    disabled={!hasAdminKey || restoreMutation.isPending}
                    className="gap-1.5 border-amber-300 text-amber-900 bg-amber-50 hover:bg-amber-100 disabled:opacity-50"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-amber-700" />
                    <span>{restoreMutation.isPending ? "Restoring..." : "Restore Version"}</span>
                  </Button>
                </div>
              )}

              <div title={!hasAdminKey ? "Unlock editing to update profile" : ""}>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsUpdateModalOpen(true)}
                  disabled={!hasAdminKey}
                  className="gap-1.5 disabled:opacity-50"
                >
                  <History className="w-3.5 h-3.5" />
                  <span>Update / Re-upload</span>
                </Button>
              </div>

              <div title={!hasAdminKey ? "Unlock editing to delete profile" : ""}>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsDeleteModalOpen(true)}
                  disabled={!hasAdminKey}
                  className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 gap-1.5 disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </Button>
              </div>
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

        {/* 3. About Card */}
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

        {/* 6. Skills Card (HIDDEN IF EMPTY) */}
        {profile.skills && profile.skills.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Award className="w-4 h-4 text-slate-500" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Skills ({profile.skills.length})
              </h2>
            </div>
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

        {/* Certifications Card (HIDDEN IF EMPTY) */}
        {profile.certifications && profile.certifications.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Award className="w-4 h-4 text-slate-500" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Certifications ({profile.certifications.length})
              </h2>
            </div>
            <div className="divide-y divide-slate-100">
              {profile.certifications.map((rawCert, idx) => {
                const cert = parseCertification(rawCert);
                if (!cert.name) return null;
                return (
                  <div key={idx} className="py-2.5 first:pt-0 last:pb-0 space-y-0.5">
                    <h3 className="text-xs font-semibold text-slate-900">{cert.name}</h3>
                    {(cert.authority || cert.year) && (
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        {cert.authority && <span>{cert.authority}</span>}
                        {cert.year && (
                          <>
                            {cert.authority && <span>·</span>}
                            <span className="text-slate-500 tabular-nums">{cert.year}</span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 7. Provenance & Audit Trail Card (Human-Readable + Collapsible Details) */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <FileText className="w-4 h-4 text-slate-500" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Provenance &amp; Verification
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Source</span>
              <span className="font-semibold text-slate-800">{profile.retrieval.source_label}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Identity Verification</span>
              <span className="font-semibold text-slate-800">
                {getHumanIdentityLabel(profile.identity_status, profile.retrieval.verification_reason)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Retrieved</span>
              <span className="text-slate-800">{formatDate(profile.retrieval.retrieved_at)}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Last Updated</span>
              <span className="text-slate-800">{formatDate(profile.updated_at || profile.created_at)}</span>
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

          {/* Collapsible Details Disclosure for Slugs and Internal IDs */}
          <details className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 group">
            <summary className="cursor-pointer font-medium hover:text-slate-800 select-none py-1">
              Internal Technical Details
            </summary>
            <div className="pt-2 pl-3 space-y-1 font-mono text-[11px] text-slate-600 bg-slate-50 p-3 rounded-lg mt-1 border border-slate-200">
              <div>slug: {profile.slug}</div>
              <div>id: {profile.id}</div>
              <div>retrieval_status: {profile.retrieval.status}</div>
              <div>identity_status: {profile.identity_status}</div>
              {profile.retrieval.candidate_url && (
                <div>candidate_url: {profile.retrieval.candidate_url}</div>
              )}
            </div>
          </details>
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
        onKeyChange={handleKeyChange}
      />
    </div>
  );
};
