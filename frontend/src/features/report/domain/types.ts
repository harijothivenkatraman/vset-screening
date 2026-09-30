export interface CompanySummary {
  slug: string;
  name: string;
  website: string | null;
  audienceLabel: string;
  stage: string | null;
  sector: string | null;
}

export interface CoverFields {
  company_name?: string;
  report_reference?: string;
  research_cutoff?: string;
  website?: string;
  [key: string]: unknown;
}

export interface ReportHeader {
  slug: string;
  name: string;
  cover: CoverFields;
  ribbon: [string, string][];
  audienceLabel: string;
  asOfDate: string | null;
  generatedAt: string | null;
  presentation: {
    action_intro?: string;
    action_part_a_title?: string;
    action_part_b_title?: string;
    action_section_title?: string;
    audience_label?: string;
    about_screen_audience_text?: string;
    [key: string]: unknown;
  };
}

export interface SectionNavItem {
  key: string;
  title: string;
  position: number;
}

export interface InfoToPrepareItem {
  id?: string;
  text: string;
  why?: string | null;
}

export interface SectionDetail {
  key: string;
  title: string;
  position: number;
  ribbon: [string, string][];
  blocks: unknown[];
  informationToPrepare: InfoToPrepareItem[];
}

export interface ConcernsData {
  concerns: unknown[];
  conflicts: unknown[];
  message: string;
}

export interface QuestionItem {
  id: string;
  text: string;
  why?: string | null;
}

export interface TopicQuestions {
  topic: string;
  items: QuestionItem[];
}

export interface DocumentGroup {
  group: string;
  priority: string[];
  secondary: string[];
}

export interface ActionsData {
  concerns: ConcernsData;
  presentation: {
    actionIntro: string;
    partATitle: string;
    partBTitle: string;
    actionSectionTitle: string;
  };
  questions: TopicQuestions[];
  documents: DocumentGroup[];
}

export interface SourceItem {
  sourceId: string;
  position: number;
  title: string;
  publisher?: string | null;
  publishedDate?: string | null;
  displayUrl?: string | null;
  canonicalUrl?: string | null;
}

export interface SourcesData {
  aboutText: string;
  limitations: string[];
  researchWindow: {
    from?: string;
    to?: string;
    [key: string]: unknown;
  };
  sources: SourceItem[];
}
