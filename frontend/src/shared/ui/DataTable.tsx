import React from "react";
import { MutedValue } from "./MutedValue";

interface DataTableProps {
  headers: string[];
  rows: unknown[][];
  widths?: number[];
  className?: string;
}

export const DataTable: React.FC<DataTableProps> = ({
  headers,
  rows,
  widths,
  className = "",
}) => {
  return (
    <div className={`overflow-x-auto rounded border border-slate-200 bg-white ${className}`}>
      <table className="w-full text-left border-collapse text-sm">
        {widths && widths.length === headers.length && (
          <colgroup>
            {widths.map((w, idx) => (
              <col key={idx} style={{ width: `${Math.round(w * 100)}%` }} />
            ))}
          </colgroup>
        )}
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            {headers.map((h, idx) => (
              <th
                key={idx}
                scope="col"
                className="py-2.5 px-3.5 text-xs font-semibold uppercase tracking-wider text-slate-600 first:pl-4 last:pr-4"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, rIdx) => (
            <tr key={rIdx} className="hover:bg-slate-50/60 transition-colors">
              {row.map((cell, cIdx) => (
                <td
                  key={cIdx}
                  className="py-2.5 px-3.5 text-slate-800 align-top leading-normal first:pl-4 last:pr-4"
                >
                  <MutedValue value={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
