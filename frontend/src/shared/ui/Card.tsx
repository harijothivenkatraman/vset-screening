import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = "", id }) => {
  return (
    <div
      id={id}
      className={`bg-white rounded-md border border-slate-200 p-5 shadow-2xs ${className}`}
    >
      {children}
    </div>
  );
};

interface CalloutProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Callout: React.FC<CalloutProps> = ({ title, children, className = "" }) => {
  return (
    <div
      className={`bg-slate-50/80 rounded-md border border-slate-200 border-l-4 border-l-[#1e2a3a] p-4.5 my-3 shadow-2xs ${className}`}
    >
      {title && (
        <h4 className="text-xs font-semibold uppercase tracking-wider text-[#1e2a3a] mb-1.5">
          {title}
        </h4>
      )}
      <div className="text-sm text-slate-800 leading-relaxed">{children}</div>
    </div>
  );
};
