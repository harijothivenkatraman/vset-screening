import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ExternalLink,
  MapPin,
  Briefcase,
  GraduationCap,
  Award,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Clock,
} from "lucide-react";
import { Avatar } from "@/shared/ui/Avatar";
import { Badge } from "@/shared/ui/Badge";
import { Card } from "@/shared/ui/Card";
import { Collapsible } from "@/shared/ui/Collapsible";
import { formatChipDate } from "@/shared/lib/date-formatter";

export interface ExperienceTimelineItem {
  title: string;
  company: string;
  start?: string;
  end?: string;
  duration?: string;
  description?: string;
  is_current?: boolean;
}

export interface EducationTimelineItem {
  school: string;
  degree?: string;
  field?: string;
  start_year?: string;
  end_year?: string;
}

export interface CrossCheckConflictItem {
  field_name: string;
  website_value: string;
  linkedin_value: string;
  details: string;
  severity: string;
}

export interface FounderRetrievalPayload {
  status:
    | "retrieved"
    | "user_provided"
    | "reference_screen"
    | "blocked_by_bot_protection"
    | "blocked"
    | "not_found"
    | "identity_unverified"
    | "not_requested";
  source_type: string;
  retrieved_at?: string;
  source_id?: string;
  sections_available?: string[];
  warnings?: string[];
  verification_reason?: string;
}

export interface FounderProfilePayload {
  founder_name: string;
  linkedin_url?: string;
  headline?: string | null;
  location?: string | null;
  about?: string | null;
  experience_timeline?: ExperienceTimelineItem[];
  education?: EducationTimelineItem[];
  skills?: string[];
  certifications?: string[];
  languages?: string[];
  retrieval?: FounderRetrievalPayload;
  cross_checks?: CrossCheckConflictItem[];
  identity_status?: "verified" | "likely_match" | "unverified";
  website_data?: {
    name: string;
    role: string;
    lines: [string, string][];
    fit?: string;
  };
}

interface FounderProfileBlockProps {
  block: [string, string, ...unknown[]];
}

export const FounderProfileBlock: React.FC<FounderProfileBlockProps> = ({ block }) => {
  const [, title, payloadRaw] = block;
  const { slug } = useParams<{ slug: string }>();
  const [aboutExpanded, setAboutExpanded] = useState<boolean>(false);
  const [experienceExpanded, setExperienceExpanded] = useState<boolean>(false);

  const data = (payloadRaw || {}) as FounderProfilePayload;
  const founderName = data.founder_name || title?.replace(/^Founder profile:\s*/i, "") || "Founder";
  const retrieval = data.retrieval || {
    status: "not_found",
    source_type: "linkedin_public",
  };

  const status = retrieval.status;
  const isBlocked = status === "blocked_by_bot_protection" || status === "blocked";
  const isNotFound = status === "not_found";
  const isIdentityUnverified = status === "identity_unverified" || data.identity_status === "likely_match";
  const isUserProvided = status === "user_provided" || retrieval.source_type === "user_supplied";
  const isRetrieved = status === "retrieved";
  const isReferenceScreen =
    retrieval.source_type === "reference_screen" ||
    status === "reference_screen" ||
    retrieval.source_type === "reference";
  const hasValidLinkedIn = Boolean(data.linkedin_url && data.linkedin_url.startsWith("http"));
  const discoverUrl = `/discover?company=${encodeURIComponent(slug || "")}&founders=${encodeURIComponent(founderName)}`;

  // ── Blocked state: compact per-founder row, neutral copy, hide LinkedIn when no URL ──
  if (isBlocked) {
    return (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 my-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50/50 transition-colors shadow-2xs">
        <div className="flex items-center gap-3.5 min-w-0">
          <Avatar name={founderName} size="md" className="shrink-0 ring-1 ring-slate-200" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-slate-900 text-sm">{founderName}</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                Not retrievable from this server
              </span>
            </div>
            {data.headline && data.headline !== "Not established" && (
              <p className="text-xs text-slate-600 truncate max-w-md mt-0.5">
                {data.headline}
              </p>
            )}
            <p className="text-[11px] text-slate-400 mt-0.5">
              Technical diagnostics recorded in Retrieval log.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 sm:self-center">
          {hasValidLinkedIn && (
            <a
              href={data.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open LinkedIn profile for ${founderName}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-md border border-slate-200 transition-colors"
            >
              <span>Open LinkedIn profile</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          <Link
            to={discoverUrl}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#0369a1] bg-[#f0f7ff] hover:bg-[#e0f2fe] rounded-md border border-[#bae6fd] transition-colors"
          >
            <span>Provide manually</span>
          </Link>
        </div>
      </div>
    );
  }

  // ── Unverified candidate: minimal row showing only name, candidate link and "Needs confirmation" ──
  if (isIdentityUnverified) {
    return (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 my-2 rounded-lg border border-amber-200 bg-amber-50/50 transition-colors shadow-2xs">
        <div className="flex items-center gap-3.5 min-w-0">
          <Avatar name={founderName} size="md" className="shrink-0 ring-1 ring-amber-200" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-slate-900 text-sm">{founderName}</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-900 border border-amber-300">
                Needs confirmation
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              Candidate profile identified but not corroborated against company domain.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0 sm:self-center">
          {hasValidLinkedIn && (
            <a
              href={data.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open candidate profile for ${founderName}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-md border border-slate-200 transition-colors"
            >
              <span>Candidate profile</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          <button
            type="button"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#0369a1] hover:bg-[#0284c7] rounded-md transition-colors"
          >
            <span>Confirm</span>
          </button>
          <Link
            to={discoverUrl}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-amber-900 bg-amber-100 hover:bg-amber-200 rounded-md border border-amber-300 transition-colors"
          >
            <span>Paste URL or profile text</span>
          </Link>
        </div>
      </div>
    );
  }

  const hasPopulatedData =
    (data.experience_timeline && data.experience_timeline.length > 0) ||
    (data.education && data.education.length > 0) ||
    Boolean(data.about && data.about !== "Not established") ||
    Boolean(data.headline && data.headline !== "Not established");

  const aboutText = data.about && data.about !== "Not established" ? data.about : null;
  const isAboutLong = Boolean(aboutText && aboutText.length > 280);

  // Missing sections to display honest empty notes
  const missingSections: string[] = [];
  if (!data.education || data.education.length === 0) {
    missingSections.push("Education credentials");
  }
  if (!data.skills || data.skills.length === 0) {
    missingSections.push("Skills & Endorsements");
  }
  if (!data.certifications || data.certifications.length === 0) {
    missingSections.push("Licenses & Certifications");
  }

  return (
    <Card className="p-6 border border-slate-200 bg-white space-y-6 shadow-xs my-4">
      {/* ── Top Header Ribbon: Avatar, Name, Headline, Source Chip, External Link ── */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-slate-100">
        <div className="flex items-start gap-4 min-w-0">
          {/* Avatar: strictly initials only, never hotlinked external images */}
          <Avatar name={founderName} size="lg" className="shrink-0 ring-2 ring-slate-100" />

          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-bold text-slate-900 tracking-tight">{founderName}</h3>

              {isReferenceScreen && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  From vSET reference screen{retrieval.retrieved_at ? ` · ${formatChipDate(retrieval.retrieved_at)}` : ""}
                </span>
              )}
              {isUserProvided && !isReferenceScreen && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                  Provided by user (unverified){retrieval.retrieved_at ? ` · ${formatChipDate(retrieval.retrieved_at)}` : ""}
                </span>
              )}
              {isRetrieved && !isReferenceScreen && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-sky-50 text-sky-800 border border-sky-200">
                  LinkedIn public{retrieval.retrieved_at ? ` · retrieved ${formatChipDate(retrieval.retrieved_at)}` : ""}
                </span>
              )}
              {isNotFound && !isReferenceScreen && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                  Profile not established
                </span>
              )}
            </div>

            {/* Headline */}
            {data.headline && data.headline !== "Not established" && (
              <p className="text-xs sm:text-sm font-medium text-slate-700 leading-snug">
                {data.headline}
              </p>
            )}

            {/* Location */}
            {data.location && data.location !== "Not established" && (
              <div className="flex items-center gap-1.5 text-xs text-slate-500 pt-0.5">
                <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>{data.location}</span>
              </div>
            )}
          </div>
        </div>

        {/* Action: Open LinkedIn Link (hidden when no URL exists) */}
        {hasValidLinkedIn && (
          <div className="flex items-center gap-2 self-start shrink-0">
            <a
              href={data.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open LinkedIn profile for ${founderName}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#0369a1] bg-[#f0f7ff] hover:bg-[#e0f2fe] rounded-md border border-[#bae6fd] transition-colors"
            >
              <span>Open LinkedIn profile</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        )}
      </div>

      {/* ── Cross-Check Conflicts ("Differences found — verify") ── */}
      {data.cross_checks && data.cross_checks.length > 0 && (
        <div className="space-y-2">
          {data.cross_checks.map((conf, i) => (
            <div
              key={i}
              className="p-3.5 bg-amber-50/80 border-l-4 border-l-amber-500 border border-amber-200 rounded-r-md text-xs space-y-1"
            >
              <div className="flex items-center gap-1.5 font-bold text-amber-800 uppercase tracking-wide text-[11px]">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Differences found — verify</span>
              </div>
              <p className="text-amber-900 leading-relaxed font-normal">{conf.details}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Not Found Fallback ── */}
      {isNotFound && !hasPopulatedData && (
        <div className="p-4 rounded-md bg-slate-50 border border-slate-200 text-slate-700 text-xs space-y-1.5">
          <div className="flex items-center gap-2 font-semibold text-slate-800">
            <HelpCircle className="w-4 h-4 text-slate-500 shrink-0" />
            <span>Public Profile Not Found</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            Public LinkedIn profile was not identified or could not be established from public search.
          </p>
          <div className="pt-1">
            <Link
              to={discoverUrl}
              className="text-[#0369a1] font-semibold hover:underline inline-flex items-center gap-1"
            >
              Provide founder details manually in Discovery &rarr;
            </Link>
          </div>
        </div>
      )}

      {/* ── About Section (collapsible if long) ── */}
      {aboutText && (
        <div className="space-y-1.5">
          {isAboutLong ? (
            <Collapsible
              id={`about-${founderName.replace(/\s+/g, "-")}`}
              title="About"
              isOpen={aboutExpanded}
              onToggle={() => setAboutExpanded(!aboutExpanded)}
            >
              <div className="p-3.5 bg-slate-50/70 rounded-md border border-slate-200/80 text-xs sm:text-sm text-slate-800 leading-relaxed font-normal mt-2">
                <p>{aboutText}</p>
              </div>
            </Collapsible>
          ) : (
            <>
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                About
              </h4>
              <div className="p-3.5 bg-slate-50/70 rounded-md border border-slate-200/80 text-xs sm:text-sm text-slate-800 leading-relaxed font-normal">
                <p>{aboutText}</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Website-Derived Details ── */}
      {data.website_data && (
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-slate-50/70 rounded-md border border-slate-200/80 text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 shrink-0">
                From company website
              </span>
              <span className="text-slate-400">·</span>
              <span className="font-semibold text-slate-900 truncate">
                {data.website_data.role}
              </span>
            </div>
            {(() => {
              const srcUrl =
                (data.website_data as { source_url?: string }).source_url ||
                data.website_data.lines?.find(([, v]) => typeof v === "string" && v.includes("http"))?.[1]?.match(/https?:\/\/[^\s]+/)?.[0];
              return srcUrl ? (
                <a
                  href={srcUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-[#0369a1] hover:underline shrink-0"
                >
                  <span>Website source</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              ) : null;
            })()}
          </div>
          {data.website_data.fit && !data.website_data.fit.toLowerCase().includes("could not be retrieved") && (
            <div className="p-3 bg-sky-50/60 border border-sky-100 rounded-md text-xs text-slate-700 leading-relaxed">
              <span className="font-bold text-[#0369a1] text-[11px] uppercase tracking-wider block mb-1">
                Founder–Market Fit
              </span>
              {data.website_data.fit}
            </div>
          )}
        </div>
      )}

      {/* ── Experience Timeline ── */}
      {data.experience_timeline && data.experience_timeline.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 text-slate-700">
            <Briefcase className="w-4 h-4 text-slate-500 shrink-0" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Experience Timeline
            </h4>
          </div>

          <div className="relative pl-5 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {(experienceExpanded ? data.experience_timeline : data.experience_timeline.slice(0, 3)).map((exp, idx) => {
              const dateRange = exp.duration || [exp.start, exp.end].filter(Boolean).join(" - ");
              return (
                <div key={idx} className="relative group text-xs space-y-1">
                  {/* Timeline node dot */}
                  <div
                    aria-hidden="true"
                    className={`absolute -left-5 mt-1.5 w-2.5 h-2.5 rounded-full ring-4 ring-white shadow-2xs ${
                      exp.is_current ? "bg-[#0369a1]" : "bg-slate-400"
                    }`}
                  />

                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">
                      {exp.title}
                    </span>
                    {exp.company && (
                      <span className="text-slate-600 font-medium">
                        · {exp.company}
                      </span>
                    )}
                    {exp.is_current && (
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">
                        Current
                      </Badge>
                    )}
                  </div>

                  {dateRange && (
                    <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
                      <Clock className="w-3 h-3 text-slate-400 shrink-0" />
                      <span>{dateRange}</span>
                    </div>
                  )}

                  {exp.description && (
                    <p className="text-slate-600 pt-0.5 leading-relaxed text-[11px]">
                      {exp.description}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
          
          {data.experience_timeline.length > 3 && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setExperienceExpanded(!experienceExpanded)}
                className="inline-flex items-center gap-1 text-xs font-semibold text-[#0369a1] hover:underline cursor-pointer"
              >
                <span>{experienceExpanded ? "Show less experience" : `Show ${data.experience_timeline.length - 3} more roles`}</span>
                {experienceExpanded ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Education ── */}
      {data.education && data.education.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-slate-100">
          <div className="flex items-center gap-1.5 text-slate-700">
            <GraduationCap className="w-4 h-4 text-slate-500 shrink-0" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Education
            </h4>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.education.map((edu, idx) => {
              const years = [edu.start_year, edu.end_year].filter(Boolean).join(" - ");
              const degreeField = [edu.degree, edu.field].filter(Boolean).join(", ");
              return (
                <div
                  key={idx}
                  className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 text-xs space-y-0.5"
                >
                  <p className="font-bold text-slate-900">{edu.school}</p>
                  {degreeField && <p className="text-slate-700 font-medium">{degreeField}</p>}
                  {years && <p className="text-[11px] text-slate-500">{years}</p>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Skills & Certifications ── */}
      {((data.skills && data.skills.length > 0) ||
        (data.certifications && data.certifications.length > 0) ||
        (data.languages && data.languages.length > 0)) && (
        <div className="space-y-3 pt-2 border-t border-slate-100">
          <div className="flex items-center gap-1.5 text-slate-700">
            <Award className="w-4 h-4 text-slate-500 shrink-0" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Skills, Certifications &amp; Languages
            </h4>
          </div>

          <div className="space-y-2 text-xs">
            {data.skills && data.skills.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide block mb-1">
                  Skills
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {data.skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-slate-100 text-slate-800 rounded text-xs font-medium border border-slate-200/80"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {data.certifications && data.certifications.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide block mb-1">
                  Certifications
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {data.certifications.map((rawCert, idx) => {
                    const label = typeof rawCert === "string" ? rawCert : ((rawCert as any)?.name || JSON.stringify(rawCert));
                    return (
                      <span
                        key={idx}
                        className="px-2 py-0.5 bg-sky-50 text-sky-900 rounded text-xs font-medium border border-sky-200"
                      >
                        {label}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            {data.languages && data.languages.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide block mb-1">
                  Languages
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {data.languages.map((lang, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-emerald-50 text-emerald-900 rounded text-xs font-medium border border-emerald-200"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Honest Note on Sections Not Exposed ── */}
      {hasPopulatedData && missingSections.length > 0 && (
        <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 italic">
          Sections not available in public footprint: {missingSections.join(", ")}.
        </div>
      )}
    </Card>
  );
};
