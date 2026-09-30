import React from "react";
import { isCalloutTitle } from "@/config/callout-titles";
import { Callout } from "@/shared/ui";

interface ParaBlockProps {
  block: [string, string, ...unknown[]];
}

export const ParaBlock: React.FC<ParaBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const text = typeof payload === "string" ? payload : String(payload || "");

  const isCallout = isCalloutTitle(title);

  if (isCallout) {
    return (
      <Callout title={title} className="my-5">
        {text}
      </Callout>
    );
  }

  return (
    <div className="my-5 space-y-1.5 max-w-3xl">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}
      <p className="text-[15px] text-slate-800 leading-relaxed font-normal">
        {text}
      </p>
    </div>
  );
};
