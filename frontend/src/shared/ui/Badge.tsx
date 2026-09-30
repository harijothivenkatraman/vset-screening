import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "navy" | "outline" | "focal" | "blue" | "success" | "warning";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
  className = "",
}) => {
  const variantClasses = {
    default: "bg-slate-100 text-slate-700 border-slate-200",
    navy: "bg-[#1e2a3a] text-white border-transparent",
    outline: "bg-white text-slate-700 border-slate-300",
    focal: "bg-[#f0f7ff] text-[#0369a1] border-[#bae6fd]",
    blue: "bg-[#f0f7ff] text-[#0369a1] border-[#bae6fd]",
    success: "bg-emerald-50 text-[#047857] border-emerald-200",
    warning: "bg-amber-50 text-[#92400e] border-amber-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border tabular-nums ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
};
