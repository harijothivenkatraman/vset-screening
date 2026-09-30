import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}) => {
  const base =
    "inline-flex items-center justify-center font-medium rounded transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer";

  const sizeClasses = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-3.5 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  };

  const variantClasses = {
    primary: "bg-[#1e2a3a] text-white hover:bg-[#2c3e56] focus-visible:outline-[#1e2a3a]",
    secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200 focus-visible:outline-slate-400",
    outline: "border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 focus-visible:outline-slate-400",
    ghost: "text-slate-600 hover:bg-slate-100 focus-visible:outline-slate-400",
  };

  return (
    <button
      className={`${base} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
