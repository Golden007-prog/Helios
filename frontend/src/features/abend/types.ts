/** Highlight span produced by the SYSLOG parser. */
export interface ParserHighlight {
  /** Byte offset into the raw SYSLOG text. */
  offset: number;
  length: number;
  kind: "abend_code" | "program" | "paragraph" | "field" | "step";
  /** The substring (cached so the renderer doesn't re-slice). */
  value: string;
}

/** Backend ``AbendResponse`` flat-aliases, what the three-pane renders. */
export interface AbendAnalysisResponse {
  pattern_code?: string;
  identified_abend: {
    code: string;
    confidence: number;
    tier: "confirmed" | "probable" | "unfamiliar" | "unknown";
  };
  failing_step: {
    step_name?: string | null;
    program?: string | null;
    offset_hex?: string | null;
  };
  source_trace: {
    file?: string | null;
    line?: number | null;
    paragraph?: string | null;
    highlighted_field?: string | null;
  };
  business_rule_explanation: string;
  ranked_root_causes: {
    cause: string;
    prior_count: number;
    confidence: number;
  }[];
  matching_runbooks: {
    id: string;
    title: string;
    success_count: number;
  }[];
  degraded: boolean;
  degraded_reason?: string | null;
  /** Optional quarantine SQL pulled from the matched runbook. The backend
   * doesn't surface this yet; the UI gates the CTA on its presence. */
  quarantine_sql?: string | null;
}
