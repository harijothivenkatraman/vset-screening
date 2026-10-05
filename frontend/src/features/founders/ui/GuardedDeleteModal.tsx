import React, { useState, useEffect } from "react";
import { AlertTriangle, Trash2, X } from "lucide-react";
import { Button } from "@/shared/ui/Button";

interface GuardedDeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  slug: string;
  founderName: string;
  isLoading: boolean;
}

export const GuardedDeleteModal: React.FC<GuardedDeleteModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  slug,
  founderName,
  isLoading,
}) => {
  const [confirmInput, setConfirmInput] = useState("");

  useEffect(() => {
    if (isOpen) {
      setConfirmInput("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const isConfirmed = confirmInput.trim() === slug;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
    >
      <div className="bg-white rounded-xl shadow-xl border border-rose-200 w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-rose-100 bg-rose-50/50">
          <div className="flex items-center gap-2 text-rose-700">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <h2 id="delete-modal-title" className="text-base font-semibold">
              Guarded Deletion
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
        <div className="p-6 space-y-4">
          <p className="text-sm text-slate-700 leading-relaxed">
            Are you sure you want to permanently delete the profile for{" "}
            <strong className="text-slate-900 font-semibold">{founderName}</strong>?
          </p>

          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 space-y-1">
            <p className="font-semibold">This action cannot be undone.</p>
            <p>All profile data, timeline items, education history, and snapshots will be removed.</p>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="confirm-slug-input"
              className="block text-xs font-medium text-slate-700"
            >
              Type the exact profile slug to confirm:
            </label>
            <div className="text-xs font-mono bg-slate-100 text-slate-800 px-2 py-1 rounded select-all mb-2">
              {slug}
            </div>
            <input
              id="confirm-slug-input"
              type="text"
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder="Type slug here..."
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-rose-500 focus:border-rose-500 font-mono"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={!isConfirmed || isLoading}
              onClick={onConfirm}
              className="bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4 mr-1.5 inline" />
              {isLoading ? "Deleting..." : "Permanently Delete"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
