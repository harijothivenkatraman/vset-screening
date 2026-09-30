import React from "react";
import { Compass, Lightbulb } from "lucide-react";

export type CalloutVariant = "position" | "analyst" | "default";

interface CalloutProps {
  title?: string;
  variant?: CalloutVariant;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function determineCalloutVariant(title?: string): CalloutVariant {
  if (!title) return "default";
  const lower = title.toLowerCase();
  if (
    lower.includes("analyst") ||
    lower.includes("differentiation") ||
    lower.includes("market fit")
  ) {
    return "analyst";
  }
  if (
    lower.includes("position") ||
    lower.includes("milestone") ||
    lower.includes("maturity")
  ) {
    return "position";
  }
  return "default";
}

export const Callout: React.FC<CalloutProps> = ({
  title,
  variant,
  icon,
  children,
  className = "",
}) => {
  const activeVariant = variant || determineCalloutVariant(title);

  const isAnalyst = activeVariant === "analyst";

  const containerClasses = isAnalyst
    ? "bg-[#f8fafc] border-slate-200 border-l-4 border-l-[#0369a1]"
    : "bg-slate-50/80 border-slate-200 border-l-4 border-l-[#1e2a3a]";

  const defaultIcon = isAnalyst ? (
    <Lightbulb className="w-4 h-4 text-[#0369a1] shrink-0" aria-hidden="true" />
  ) : (
    <Compass className="w-4 h-4 text-[#1e2a3a] shrink-0" aria-hidden="true" />
  );

  const titleColor = isAnalyst ? "text-[#0369a1]" : "text-[#1e2a3a]";

  return (
    <div
      role="region"
      aria-label={title || "Key finding"}
      className={`rounded-lg border p-4.5 my-4 shadow-2xs ${containerClasses} ${className}`}
    >
      {title && (
        <div className="flex items-center gap-2 mb-2">
          {icon || defaultIcon}
          <h4 className={`text-[11px] font-bold uppercase tracking-wider ${titleColor}`}>
            {title}
          </h4>
        </div>
      )}
      <div className="text-sm text-slate-800 leading-relaxed font-normal pl-6">
        {children}
      </div>
    </div>
  );
};
