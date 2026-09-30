import React from "react";
import { formatDisplayDate } from "@/shared/lib/date-formatter";
import { MutedValue } from "./MutedValue";
import { Badge } from "./Badge";

export interface FundingEvent {
  date: string;
  financing: string;
  amount: string;
  investors: string;
  details?: string;
}

interface FundingCardsProps {
  events: FundingEvent[];
  className?: string;
}

/**
 * Splits an investors string on commas only, preserving all words and text.
 * Returns empty array if value is missing or 'Not disclosed'.
 */
export function splitInvestors(investorsStr: string): string[] {
  if (
    !investorsStr ||
    investorsStr === "-" ||
    investorsStr.toLowerCase() === "not disclosed"
  ) {
    return [];
  }
  return investorsStr
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Validates whether table headers represent a Funding History table.
 */
export function isFundingTable(headers: string[]): boolean {
  if (!headers || headers.length < 4) return false;
  const normalized = headers.map((h) => h.trim().toLowerCase());
  const hasDate = normalized.some((h) => h.includes("date"));
  const hasFinancing = normalized.some(
    (h) => h.includes("financing") || h.includes("round")
  );
  const hasAmount = normalized.some((h) => h.includes("amount"));
  const hasInvestors = normalized.some((h) => h.includes("investor"));
  return hasDate && hasFinancing && hasAmount && hasInvestors;
}

/**
 * Maps raw table headers and rows to typed FundingEvent objects.
 */
export function parseFundingRows(
  headers: string[],
  rows: unknown[][]
): FundingEvent[] {
  const dateIdx = headers.findIndex((h) => /date/i.test(h));
  const finIdx = headers.findIndex((h) => /financ|round/i.test(h));
  const amtIdx = headers.findIndex((h) => /amount/i.test(h));
  const invIdx = headers.findIndex((h) => /investor|provider/i.test(h));
  const detIdx = headers.findIndex((h) => /detail|note|intended/i.test(h));

  return rows.map((r) => {
    const row = Array.isArray(r) ? r : [];
    return {
      date: String(row[dateIdx] ?? ""),
      financing: String(row[finIdx] ?? ""),
      amount: String(row[amtIdx] ?? ""),
      investors: String(row[invIdx] ?? ""),
      details: detIdx !== -1 ? String(row[detIdx] ?? "") : undefined,
    };
  });
}

export const FundingCards: React.FC<FundingCardsProps> = ({
  events,
  className = "",
}) => {
  if (!events || events.length === 0) return null;

  return (
    <div
      className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}
    >
      {events.map((event, idx) => {
        const isUndated =
          !event.date ||
          event.date === "-" ||
          event.date.toLowerCase() === "undated";

        const isAmountUndisclosed =
          !event.amount ||
          event.amount === "-" ||
          event.amount.toLowerCase() === "not disclosed";

        const investorList = splitInvestors(event.investors);
        const hasDetails =
          event.details &&
          event.details.trim() !== "" &&
          event.details.trim() !== "-";

        return (
          <div
            key={idx}
            className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors"
          >
            <div>
              {/* Header: Round Badge and Date */}
              <div className="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-100">
                <Badge variant="blue" className="text-xs font-semibold">
                  {event.financing || "Financing Round"}
                </Badge>
                {isUndated ? (
                  <span className="text-xs text-slate-400 italic bg-slate-50 px-2 py-0.5 rounded border border-slate-200/60">
                    Undated
                  </span>
                ) : (
                  <span className="text-xs font-semibold text-slate-700 tabular-nums px-2 py-0.5 rounded bg-slate-100 border border-slate-200/80">
                    {formatDisplayDate(event.date)}
                  </span>
                )}
              </div>

              {/* Amount Hero */}
              <div className="my-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5">
                  Amount Raised
                </span>
                {isAmountUndisclosed ? (
                  <div className="text-sm font-medium text-slate-400 italic">
                    <MutedValue value="Not disclosed" />
                  </div>
                ) : (
                  <div className="text-2xl font-bold text-slate-900 tracking-tight">
                    {event.amount}
                  </div>
                )}
              </div>

              {/* Investors / Providers */}
              <div className="mt-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                  Investors & Providers
                </span>
                {investorList.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {investorList.map((inv, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200/70"
                      >
                        {inv}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-slate-500">
                    <MutedValue value={event.investors || "Not disclosed"} />
                  </div>
                )}
              </div>
            </div>

            {/* Key Details */}
            {hasDetails && (
              <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 leading-relaxed font-normal bg-slate-50/70 p-2.5 rounded border border-slate-100">
                <span className="font-semibold text-slate-700">Details: </span>
                {event.details}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
