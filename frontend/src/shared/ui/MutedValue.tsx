import React from "react";

interface MutedValueProps {
  value: unknown;
  className?: string;
  tooltip?: string;
}

export function isUnavailable(val: unknown): boolean {
  if (val === null || val === undefined) return true;
  const str = String(val).trim();
  return (
    str === "" ||
    str === "-" ||
    str === "–" ||
    str === "—" ||
    str.toLowerCase() === "not established" ||
    str.toLowerCase() === "not disclosed" ||
    str.toLowerCase() === "none identified" ||
    str.toLowerCase() === "undated"
  );
}

export const MutedValue: React.FC<MutedValueProps> = ({
  value,
  className = "",
  tooltip = "Not established from public sources",
}) => {
  if (isUnavailable(value)) {
    const rawStr = value !== null && value !== undefined ? String(value).trim() : "";
    const lower = rawStr.toLowerCase();

    let text = "Not established";
    if (lower === "not disclosed") {
      text = "Not disclosed";
    } else if (lower === "undated") {
      text = "Undated";
    }

    return (
      <span
        title={tooltip}
        className={`text-slate-500 italic text-sm cursor-help select-none ${className}`}
      >
        {text}
      </span>
    );
  }

  return <span className={className}>{String(value)}</span>;
};
