import React from "react";
import { MutedValue } from "@/shared/ui";

interface ComparisonObject {
  header?: string[];
  items?: [string, string, string][];
  rows?: unknown[][];
  mode?: string;
  note?: string;
}

interface ComparisonBlockProps {
  block: [string, string, ...unknown[]];
}

export const ComparisonBlock: React.FC<ComparisonBlockProps> = ({ block }) => {
  const [, title, payload] = block;
  const comp = (payload || {}) as ComparisonObject;

  const hasItems = Array.isArray(comp.items) && comp.items.length > 0;
  const hasRows =
    Array.isArray(comp.rows) &&
    comp.rows.length > 0 &&
    Array.isArray(comp.header) &&
    comp.header.length > 0;

  return (
    <div className="my-6 space-y-3">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}

      {/* Shape (a): 2 columns (criterion with muted description beneath, then the company position) */}
      {hasItems && comp.items && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-xs">
          <table className="w-full text-left border-collapse text-sm">
            <colgroup>
              <col className="w-2/5 min-w-[240px]" />
              <col className="w-3/5 min-w-[300px]" />
            </colgroup>
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th
                  scope="col"
                  className="py-3 px-4 text-xs font-bold uppercase tracking-wider text-slate-600"
                >
                  Criterion & Context
                </th>
                <th
                  scope="col"
                  className="py-3 px-4 text-xs font-bold uppercase tracking-wider text-slate-600"
                >
                  Company Position
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {comp.items.map(([criterion, desc, position], idx) => (
                <tr
                  key={idx}
                  className="hover:bg-slate-50/70 transition-colors"
                >
                  <td className="py-3.5 px-4 align-top">
                    <div className="font-semibold text-slate-900 text-sm leading-snug">
                      {criterion}
                    </div>
                    {desc && (
                      <div className="text-xs text-slate-500 mt-1 leading-relaxed font-normal">
                        {desc}
                      </div>
                    )}
                  </td>
                  <td className="py-3.5 px-4 align-top text-sm text-slate-800 leading-relaxed font-normal">
                    <MutedValue value={position} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Shape (b): Matrix table with sticky header, sticky first column, and highlighted company column */}
      {hasRows && comp.header && comp.rows && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-xs max-h-[600px] overflow-y-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="sticky top-0 z-20 shadow-xs">
              <tr className="border-b border-slate-200 bg-slate-50">
                {comp.header.map((colName, cIdx) => {
                  const isFirst = cIdx === 0;
                  const isCompany = cIdx === 1;

                  return (
                    <th
                      key={cIdx}
                      scope="col"
                      className={`py-3 px-3.5 text-xs font-bold uppercase tracking-wider whitespace-nowrap ${
                        isFirst
                          ? "sticky left-0 bg-slate-50 z-30 text-slate-700 min-w-[220px] shadow-[1px_0_0_0_#e2e8f0]"
                          : isCompany
                          ? "bg-sky-50 text-sky-900 min-w-[180px] border-b-2 border-b-sky-500 border-x border-sky-200"
                          : "text-slate-600 min-w-[180px]"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span>{colName}</span>
                        {isCompany && (
                          <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-sky-200/80 text-sky-900 ml-1">
                            Subject
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {comp.rows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="hover:bg-slate-50/70 transition-colors"
                >
                  {row.map((cell, cIdx) => {
                    const isFirst = cIdx === 0;
                    const isCompany = cIdx === 1;
                    const cellStr = String(cell ?? "");

                    return (
                      <td
                        key={cIdx}
                        className={`py-3 px-3.5 align-top leading-relaxed ${
                          isFirst
                            ? "sticky left-0 bg-white z-10 font-medium text-slate-900 shadow-[1px_0_0_0_#e2e8f0]"
                            : isCompany
                            ? "bg-sky-50/40 text-slate-900 font-medium border-x border-sky-100"
                            : "text-slate-700"
                        }`}
                      >
                        <MutedValue value={cellStr} />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Note footnote per spec requirement */}
      {comp.note && (
        <div className="mt-2.5 p-3 rounded-md bg-slate-50 border border-slate-200/80 text-xs text-slate-600 leading-relaxed font-normal">
          <span className="font-semibold text-slate-700">Note: </span>
          {comp.note}
        </div>
      )}
    </div>
  );
};
