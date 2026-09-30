import React, { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

interface UnknownBlockProps {
  block: [string, string, ...unknown[]];
}

export const UnknownBlock: React.FC<UnknownBlockProps> = ({ block }) => {
  const [type, title, ...rest] = block;

  useEffect(() => {
    console.warn(`[vSET Renderer] Unknown or unregistered block type encountered: "${type}"`, {
      title,
      payload: rest,
    });
  }, [type, title, rest]);

  return (
    <div
      role="region"
      aria-label={`Unrecognized content block: ${type}`}
      className="my-4 p-4 rounded-md border border-amber-200 bg-amber-50/50 text-slate-800 space-y-2 text-xs"
    >
      <div className="flex items-center gap-2 text-amber-800 font-semibold">
        <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
        <span>Unsupported Block Type: <code className="font-mono bg-amber-100 px-1 py-0.5 rounded">{type}</code></span>
      </div>
      {title && <h4 className="font-semibold text-slate-700">{title}</h4>}
      <pre className="p-2 bg-white rounded border border-amber-200 overflow-x-auto text-[11px] text-slate-600">
        {JSON.stringify(rest, null, 2)}
      </pre>
    </div>
  );
};
