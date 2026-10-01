import React from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  Loader2,
  RotateCcw,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Badge } from "@/shared/ui/Badge";
import { useDiscoveryJobStatus } from "../hooks";

interface JobProgressProps {
  jobId: string;
  onReset: () => void;
}

const STAGES = [
  { label: "Queued", threshold: 0.05 },
  { label: "Scraping company LinkedIn", threshold: 0.15 },
  { label: "Scraping founder profiles", threshold: 0.3 },
  { label: "Fetching website pages", threshold: 0.45 },
  { label: "Fetching news articles", threshold: 0.6 },
  { label: "Extracting report data", threshold: 0.8 },
  { label: "Saving report", threshold: 0.95 },
  { label: "Complete", threshold: 1.0 },
];

export const JobProgress: React.FC<JobProgressProps> = ({ jobId, onReset }) => {
  const { data: job, isLoading, error } = useDiscoveryJobStatus(jobId);

  if (isLoading || !job) {
    return (
      <Card className="p-8 max-w-xl mx-auto text-center border border-slate-200">
        <Loader2 className="w-8 h-8 text-[#1e2a3a] animate-spin mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">Connecting to Discovery Worker...</h3>
        <p className="text-xs text-slate-500 mt-1">Checking job queue status</p>
      </Card>
    );
  }

  const isFailed = job.state === "failed";
  const isDone = job.state === "succeeded" || job.state === "partial";
  const percent = Math.round(job.progress * 100);

  return (
    <Card className="p-8 max-w-2xl mx-auto border border-slate-200 shadow-sm space-y-6">
      <div className="text-center">
        <div className="inline-flex p-3 rounded-full bg-slate-100 text-[#1e2a3a] mb-3">
          {isDone ? (
            <FileCheck2 className="w-8 h-8 text-emerald-600" />
          ) : isFailed ? (
            <AlertCircle className="w-8 h-8 text-rose-600" />
          ) : (
            <Sparkles className="w-8 h-8 text-[#0369a1] animate-pulse" />
          )}
        </div>

        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          {isDone
            ? `Report Ready: ${job.company_name}`
            : isFailed
            ? "Discovery Job Encountered an Error"
            : `Discovering ${job.company_name}`}
        </h2>

        <p className="text-sm text-slate-500 mt-1" aria-live="polite">
          {isDone
            ? "Public footprint gathered, verified, and synthesized into a standard 9-tab screening report."
            : isFailed
            ? job.error_message || "An unexpected error occurred during report extraction."
            : `Current stage: ${job.stage} (${percent}%)`}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-semibold text-slate-600">
          <span>{job.stage}</span>
          <span>{percent}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
          <div
            className={`h-full transition-all duration-500 ease-out rounded-full ${
              isDone ? "bg-emerald-500" : isFailed ? "bg-rose-500" : "bg-[#1e2a3a]"
            }`}
            style={{ width: `${Math.max(percent, 5)}%` }}
          />
        </div>
      </div>

      {/* Stage Checklist */}
      <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
        <p className="font-semibold text-slate-700 uppercase tracking-wider text-[10px] mb-2">
          Pipeline Stages
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {STAGES.map((s, idx) => {
            const isCompleted = job.progress >= s.threshold;
            const isCurrent =
              !isDone &&
              !isFailed &&
              job.progress < s.threshold &&
              (idx === 0 || job.progress >= STAGES[idx - 1].threshold);

            return (
              <div
                key={idx}
                className={`flex items-center gap-2 p-1.5 rounded transition-colors ${
                  isCompleted
                    ? "text-emerald-800 font-medium"
                    : isCurrent
                    ? "text-[#0369a1] font-semibold bg-white border border-[#bae6fd]"
                    : "text-slate-400"
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[#0369a1] shrink-0" />
                ) : (
                  <div className="w-3.5 h-3.5 rounded-full border border-slate-300 shrink-0" />
                )}
                <span className="truncate">{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Warnings List if any */}
      {job.warnings && job.warnings.length > 0 && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-md space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Notices during data collection ({job.warnings.length}):</span>
          </div>
          <ul className="list-disc list-inside text-[11px] text-amber-800 space-y-0.5">
            {job.warnings.map((w, idx) => (
              <li key={idx} className="truncate">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="pt-2 flex items-center justify-center gap-3">
        {isDone && job.result_slug && (
          <Link to={`/companies/${job.result_slug}/company`} className="w-full sm:w-auto">
            <Button size="lg" className="w-full sm:w-auto shadow-md">
              <span className="flex items-center gap-2">
                <FileCheck2 className="w-4 h-4" />
                View Startup Screening Dashboard
              </span>
            </Button>
          </Link>
        )}

        {(isFailed || isDone) && (
          <Button
            variant={isDone ? "outline" : "primary"}
            size="lg"
            onClick={onReset}
            className="w-full sm:w-auto"
          >
            <span className="flex items-center gap-2">
              <RotateCcw className="w-4 h-4" />
              Discover Another Company
            </span>
          </Button>
        )}
      </div>
    </Card>
  );
};
