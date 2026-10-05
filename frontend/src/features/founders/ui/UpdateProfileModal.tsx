import React, { useState, useEffect } from "react";
import { History, X, AlertCircle, AlertTriangle, ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { useUpdateFounder } from "../hooks";
import { FounderProfile } from "../types";
import { getAdminKey } from "./AdminKeyModal";

interface UpdateProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: FounderProfile;
}

export const UpdateProfileModal: React.FC<UpdateProfileModalProps> = ({
  isOpen,
  onClose,
  profile,
}) => {
  const [evidenceText, setEvidenceText] = useState("");
  const [notes, setNotes] = useState(profile.notes || "");
  const [screeningAssessment, setScreeningAssessment] = useState(
    profile.screening_assessment || ""
  );
  const [isConfirming, setIsConfirming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const updateMutation = useUpdateFounder();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isConfirming) {
      // First show what will change
      setIsConfirming(true);
      return;
    }

    setErrorMsg(null);
    const adminKey = getAdminKey() || undefined;

    try {
      await updateMutation.mutateAsync({
        slug: profile.slug,
        data: {
          evidence_text: evidenceText.trim() ? evidenceText.trim() : null,
          notes: notes.trim() ? notes.trim() : null,
          screening_assessment: screeningAssessment.trim() ? screeningAssessment.trim() : null,
        },
        apiKey: adminKey,
      });
      setIsConfirming(false);
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to update profile.");
      }
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="update-profile-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-sky-600" />
            <h2 id="update-profile-modal-title" className="text-base font-semibold text-slate-900">
              {isConfirming ? "Confirm Profile Update" : `Update Profile · ${profile.founder_name}`}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{errorMsg}</span>
            </div>
          )}

          {isConfirming ? (
            /* Confirmation Review Step: Show what will change */
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-xs text-amber-900">
                <div className="flex items-center gap-2 font-semibold">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Review Changes Before Saving</span>
                </div>
                <p>
                  A snapshot of the current version will be archived automatically. You can restore it at any time.
                </p>
              </div>

              <div className="space-y-3 text-xs divide-y divide-slate-100">
                <div className="pt-2">
                  <span className="font-semibold text-slate-700 block mb-1">Timeline &amp; Evidence:</span>
                  {evidenceText.trim() ? (
                    <div className="flex items-center gap-2 text-sky-700">
                      <span>Current {profile.experience_timeline.length} roles</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span className="font-semibold">Re-parsing from new evidence text</span>
                    </div>
                  ) : (
                    <span className="text-slate-500">Unchanged (preserving existing timeline &amp; education)</span>
                  )}
                </div>

                <div className="pt-2">
                  <span className="font-semibold text-slate-700 block mb-1">Screening Assessment:</span>
                  {screeningAssessment.trim() !== (profile.screening_assessment || "") ? (
                    <div className="text-emerald-700 font-medium">Updating assessment notes</div>
                  ) : (
                    <span className="text-slate-500">Unchanged</span>
                  )}
                </div>

                <div className="pt-2">
                  <span className="font-semibold text-slate-700 block mb-1">Operator Notes:</span>
                  {notes.trim() !== (profile.notes || "") ? (
                    <div className="text-emerald-700 font-medium">Updating operator notes</div>
                  ) : (
                    <span className="text-slate-500">Unchanged</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
                <Button type="button" variant="outline" size="sm" onClick={() => setIsConfirming(false)}>
                  Back to Edit
                </Button>
                <Button type="submit" variant="primary" size="sm" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Saving..." : "Confirm & Save"}
                </Button>
              </div>
            </div>
          ) : (
            /* Edit Form */
            <>
              <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg text-xs text-sky-900 space-y-1">
                <p className="font-semibold flex items-center gap-1.5">
                  <span>Automatic Snapshot Protection</span>
                </p>
                <p>
                  Updating creates a restorable snapshot of the current profile version.
                  You can restore the previous version at any time using <strong>Restore Version</strong>.
                </p>
              </div>

              <div>
                <label
                  htmlFor="update-evidence-text"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  New Profile Evidence Text (Optional)
                </label>
                <textarea
                  id="update-evidence-text"
                  rows={5}
                  value={evidenceText}
                  onChange={(e) => setEvidenceText(e.target.value)}
                  placeholder="Paste updated online profile experience / education text to re-parse and merge..."
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 font-mono"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Leave blank to keep existing parsed timeline and update only notes/assessment.
                </p>
              </div>

              <div>
                <label
                  htmlFor="update-screening-assessment"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  Screening Assessment (Shown under &quot;From vSET screening&quot;)
                </label>
                <textarea
                  id="update-screening-assessment"
                  rows={3}
                  value={screeningAssessment}
                  onChange={(e) => setScreeningAssessment(e.target.value)}
                  placeholder="Add screening fit notes or commentary from analyst report..."
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div>
                <label
                  htmlFor="update-notes"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  Internal Operator Notes
                </label>
                <textarea
                  id="update-notes"
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Internal comments, verification logs, or rationale..."
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button type="button" variant="outline" size="sm" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm">
                  Review Changes
                </Button>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  );
};
