import React from "react";

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = "" }) => {
  return <div className={`animate-pulse bg-slate-200 rounded ${className}`} />;
};

export const ReportSkeleton: React.FC = () => {
  return (
    <div className="space-y-6 max-w-(--content-max-width) py-6">
      <div className="space-y-2">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="bg-white p-6 rounded-md border border-slate-200 space-y-4">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
      </div>
      <div className="bg-white p-6 rounded-md border border-slate-200 space-y-4">
        <Skeleton className="h-5 w-44" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
};
