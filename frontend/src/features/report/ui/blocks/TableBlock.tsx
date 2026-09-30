import React from "react";
import {
  DataTable,
  Timeline,
  FundingCards,
  isFundingTable,
  parseFundingRows,
} from "@/shared/ui";

interface TableBlockProps {
  block: [string, string, ...unknown[]];
}

function isTimelineTable(headers: string[]): boolean {
  if (headers.length !== 2) return false;
  return /date/i.test(headers[0]) && /event/i.test(headers[1]);
}

export const TableBlock: React.FC<TableBlockProps> = ({ block }) => {
  const [, title, headersPayload, rowsPayload, widthsPayload] = block;

  const headers = Array.isArray(headersPayload) ? (headersPayload as string[]) : [];
  const rows = Array.isArray(rowsPayload) ? (rowsPayload as unknown[][]) : [];
  const widths = Array.isArray(widthsPayload) ? (widthsPayload as number[]) : undefined;

  const isFunding = isFundingTable(headers);
  const isTimeline = !isFunding && isTimelineTable(headers);

  return (
    <div className="my-6 space-y-3">
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {title}
        </h3>
      )}

      {isFunding ? (
        <FundingCards events={parseFundingRows(headers, rows)} />
      ) : isTimeline ? (
        <Timeline
          events={rows.map((r) => {
            const row = Array.isArray(r) ? r : [];
            return {
              date: String(row[0] ?? ""),
              event: String(row[1] ?? ""),
            };
          })}
        />
      ) : (
        <DataTable headers={headers} rows={rows} widths={widths} />
      )}
    </div>
  );
};
