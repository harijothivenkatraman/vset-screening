import React, { useState, useEffect } from "react";
import { KeyRound, ShieldCheck, ShieldAlert, X } from "lucide-react";
import { Button } from "@/shared/ui/Button";

interface AdminKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onKeyChange?: (hasKey: boolean) => void;
}

export const ADMIN_KEY_STORAGE_KEY = "founder_profiles_admin_key";

export function getAdminKey(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ADMIN_KEY_STORAGE_KEY);
}

export const AdminKeyModal: React.FC<AdminKeyModalProps> = ({
  isOpen,
  onClose,
  onKeyChange,
}) => {
  const [apiKey, setApiKey] = useState("");
  const [currentKey, setCurrentKey] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const existing = getAdminKey();
      setCurrentKey(existing);
      setApiKey(existing || "");
    }
  }, [isOpen]);

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

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = apiKey.trim();
    if (trimmed) {
      sessionStorage.setItem(ADMIN_KEY_STORAGE_KEY, trimmed);
      setCurrentKey(trimmed);
      onKeyChange?.(true);
    } else {
      sessionStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
      setCurrentKey(null);
      onKeyChange?.(false);
    }
    onClose();
  };

  const handleLock = () => {
    sessionStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
    setCurrentKey(null);
    setApiKey("");
    onKeyChange?.(false);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-key-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-slate-700" />
            <h2 id="admin-key-modal-title" className="text-base font-semibold text-slate-900">
              {currentKey ? "Editing Unlocked" : "Unlock Editing"}
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
        <form onSubmit={handleSave} className="p-6 space-y-4">
          <div className="text-xs text-slate-600 leading-relaxed space-y-2">
            <p>
              Public profiles, searches, and catalog entries are readable without authentication.
            </p>
            <p>
              Unlocking editing requires the administrative API key (sent over HTTPS only and stored in temporary sessionStorage).
            </p>
          </div>

          {currentKey ? (
            <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800">
              <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>Editing unlocked for this browser session.</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
              <ShieldAlert className="w-4 h-4 shrink-0 text-amber-600" />
              <span>Editing is locked. Enter key to unlock write actions.</span>
            </div>
          )}

          <div>
            <label
              htmlFor="admin-key-input"
              className="block text-xs font-medium text-slate-700 mb-1"
            >
              Admin Key
            </label>
            <input
              id="admin-key-input"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste admin key here..."
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 focus:border-sky-500 font-mono"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            {currentKey ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleLock}
                className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
              >
                Lock editing
              </Button>
            ) : <span />}
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm">
                Unlock editing
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
