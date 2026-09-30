import React from "react";
import { AlertCircle, FileQuestion, RefreshCw } from "lucide-react";
import { Button } from "./Button";

interface EmptyStateProps {
  title?: string;
  message: string;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No data recorded",
  message,
  className = "",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 bg-slate-50 border border-slate-200 border-dashed rounded-md text-center ${className}`}
    >
      <FileQuestion className="w-8 h-8 text-slate-400 mb-2 stroke-[1.5]" />
      <h4 className="text-sm font-semibold text-slate-700 mb-1">{title}</h4>
      <p className="text-xs text-slate-500 max-w-md leading-relaxed">{message}</p>
    </div>
  );
};

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Unable to load data",
  message = "An unexpected error occurred while fetching information from the server.",
  onRetry,
  className = "",
}) => {
  return (
    <div
      role="alert"
      className={`p-6 bg-red-50/50 border border-red-200 rounded-md text-slate-900 ${className}`}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-red-900">{title}</h4>
          <p className="text-xs text-red-700 leading-relaxed">{message}</p>
          {onRetry && (
            <div className="pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 text-xs text-slate-700"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
