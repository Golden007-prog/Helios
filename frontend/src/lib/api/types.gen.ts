// AUTO-GENERATED — do not edit by hand.
// Source: backend/app/models/**/*.py via shared/codegen/pydantic_to_typescript.py
// Run `make typegen` to regenerate.

export interface AbendContext {
  "region": string;
  "job_name": string;
  "occurred_at"?: string | null;
}

export interface AbendPriorEntry {
  "cause": string;
  "prior_count": number;
  "confidence": number;
}

export interface AbendPriorsResponse {
  "abend_code": string;
  "program"?: string | null;
  "priors": Array<AbendPriorEntry>;
}

export interface AbendRequest {
  "raw_text": string;
  "context": AbendContext;
}

export interface AbendResolveRequest {
  "root_cause_choice": string;
  "applied_runbook_id"?: string | null;
  "outcome": string;
  "notes"?: string | null;
}

export interface AbendResolveResponse {
  "event_id": string;
  "audit_event_id": string;
  "learning_event_id": string;
}

export interface AbendResponse {
  "identified_abend": IdentifiedAbend;
  "failing_step": FailingStep;
  "source_trace": SourceTrace;
  "business_rule_explanation": string;
  "ranked_root_causes": Array<RankedRootCause>;
  "matching_runbooks": Array<MatchingRunbook>;
  "degraded"?: boolean;
  "degraded_reason"?: string | null;
}

export type AbendTier = "confirmed" | "probable" | "unfamiliar" | "unknown";

export interface AppliesTo {
  "abend_code": string;
  "program"?: string | null;
  "paragraph"?: string | null;
}

export interface AttestationResponse {
  "date": string;
  "chain_root_hash": string;
  "event_count": number;
}

export interface AuditBundleRequest {
  "subject_kind"?: string | null;
  "subject_name"?: string | null;
  "subject_region"?: string | null;
  "actor"?: string | null;
  "type"?: string | null;
  "from"?: string | null;
  "to"?: string | null;
}

export interface AuditBundleResponse {
  "bundle_job_id": string;
}

export interface AuditBundleStatusResponse {
  "bundle_job_id": string;
  "state": string;
  "download_url"?: string | null;
  "error"?: string | null;
}

export interface AuditChain {
  "prev_event_id"?: string | null;
  "prev_event_hash"?: string | null;
  "this_event_hash": string;
}

export interface AuditEvent {
  "_id": string;
  "type": string;
  "actor": string;
  "actor_role": string;
  "ts": string;
  "ts_unix_ms": number;
  "subject": Record<string, unknown>;
  "before_sha256"?: string | null;
  "after_sha256"?: string | null;
  "result": string;
  "error"?: string | null;
  "client_meta"?: Record<string, unknown>;
  "chain": AuditChain;
}

export interface AuditQueryResponse {
  "events": Array<AuditEvent>;
  "bookmark"?: string | null;
}

export interface AuthenticatedUser {
  "user_id": string;
  "email": string;
  "display_name": string;
  "roles": Array<Role>;
  "shop"?: string;
}

export interface AutoFix {
  "fix": string;
  "target"?: string | null;
  "details"?: Record<string, unknown>;
}

export interface Db2Config {
  "subsystem_id": string;
  "plan_collection": string;
  "default_bind"?: Record<string, string>;
}

export interface DiffField {
  "path": string;
  "a"?: unknown | null;
  "b"?: unknown | null;
  "kind": string;
}

export interface DissentResponse {
  "rule_id": string;
  "region"?: string | null;
  "dissent_count": number;
  "dissent_total": number;
  "common_reasons"?: Array<string>;
}

export interface FailingStep {
  "step_name"?: string | null;
  "program"?: string | null;
  "offset_hex"?: string | null;
}

export interface Finding {
  "id": string;
  "rule_id": string;
  "severity": Severity;
  "description": string;
  "details"?: Record<string, unknown>;
  "subject": Subject;
  "state"?: FindingState;
  "auto_fix_available"?: boolean;
  "dissent_count"?: number | null;
  "dissent_total"?: number | null;
  "common_dismiss_reasons"?: Array<string>;
}

export interface FindingAutoFixResponse {
  "finding_id": string;
  "fix_applied": string;
  "new_score"?: number | null;
  "audit_event_id": string;
}

export interface FindingDecideRequest {
  "decision": FindingState;
  "reason": string;
  "reason_tags"?: Array<string>;
}

export interface FindingDecideResponse {
  "finding_id": string;
  "state": FindingState;
  "decided_at": string;
  "audit_event_id": string;
  "learning_event_id": string;
}

export type FindingState = "open" | "accepted" | "dismissed" | "superseded";

export interface FixAction {
  "label": string;
  "type": FixActionType;
  "language"?: string | null;
  "code"?: string | null;
}

export type FixActionType = "sql" | "jcl" | "shell" | "manual";

export interface IdentifiedAbend {
  "code": string;
  "message_id"?: string | null;
  "confidence": number;
  "tier": AbendTier;
}

export interface JCLArtifact {
  "name": string;
  "region": string;
  "state": JCLState;
  "source_blob_sha256": string;
  "source_blob_ref"?: string | null;
  "promoted_from"?: PromotedFrom | null;
  "current_confidence_score"?: number | null;
  "current_confidence_breakdown"?: Record<string, number | number>;
  "open_findings_count"?: number;
  "last_modified_event_id"?: string | null;
}

export interface JCLHistoryEntry {
  "event_id": string;
  "type": string;
  "actor": string;
  "ts": string;
}

export interface JCLHistoryResponse {
  "artifact": string;
  "region": string;
  "events": Array<JCLHistoryEntry>;
}

export interface JCLListItem {
  "name": string;
  "region": string;
  "state": JCLState;
  "current_confidence_score"?: number | null;
}

export interface JCLListResponse {
  "artifacts": Array<JCLListItem>;
  "total": number;
}

export type JCLState = "draft" | "promoted" | "archived";

export interface JCLUpsertRequest {
  "source": string;
  "reason": string;
}

export interface JCLUpsertResponse {
  "name": string;
  "region": string;
  "source_blob_sha256": string;
  "audit_event_id": string;
  "state": JCLState;
}

export interface JesConfig {
  "class": string;
  "sysout_class": string;
}

export interface LoginRequest {
  "email": string;
  "password": string;
}

export interface LoginResponse {
  "token": string;
  "expires_at": string;
  "user": AuthenticatedUser;
}

export interface MatchingRunbook {
  "id": string;
  "title": string;
  "success_count": number;
}

export interface MeResponse {
  "user": AuthenticatedUser;
}

export interface PromoteCancelResponse {
  "promote_event_id": string;
  "state": ReviewState;
}

export interface PromoteRequest {
  "jcl_name": string;
  "source_region": string;
  "target_region": string;
  "auto_apply_fixes"?: Array<string>;
  "reason"?: string | null;
}

export interface PromoteResponse {
  "promote_event_id": string;
  "diff": Array<Record<string, unknown>>;
  "confidence_score": number;
  "confidence_breakdown"?: Record<string, number | number>;
  "auto_fixes_applied": Array<AutoFix>;
  "auto_fixes_available_but_not_applied"?: Array<AutoFix>;
  "state": ReviewState;
  "reviewer"?: string | null;
}

export interface PromotedFrom {
  "region": string;
  "blob_sha256": string;
  "promote_event_id": string;
}

export interface QueueDecisionRequest {
  "reason": string;
}

export interface QueueDecisionResponse {
  "event_id": string;
  "state": ReviewState;
  "decided_by": string;
  "decided_at": string;
  "audit_event_id": string;
}

export interface QueueItem {
  "event_id": string;
  "type": string;
  "initiator": string;
  "ts": string;
  "state": ReviewState;
  "confidence_score"?: number | null;
  "summary"?: Record<string, unknown>;
}

export interface QueueListResponse {
  "items": Array<QueueItem>;
  "pending_count": number;
  "last_seq"?: string | null;
}

export interface QueueSinceResponse {
  "items": Array<QueueItem>;
  "last_seq": string;
}

export interface RankedRootCause {
  "cause": string;
  "prior_count": number;
  "confidence": number;
}

export interface RegionDiffResponse {
  "a": string;
  "b": string;
  "fields": Array<DiffField>;
}

export interface RegionForkRequest {
  "overrides": Record<string, unknown>;
  "reason": string;
}

export interface RegionForkResponse {
  "region": string;
  "job_name": string;
  "audit_event_id": string;
}

export interface RegionListItem {
  "name": string;
  "tier": RegionTier;
  "hlq": string;
}

export interface RegionListResponse {
  "regions": Array<RegionListItem>;
  "total": number;
}

export interface RegionProfile {
  "name": string;
  "tier": RegionTier;
  "hlq": string;
  "db2"?: Db2Config | null;
  "racf_group"?: string | null;
  "jes"?: JesConfig | null;
  "scheduler_queue"?: string | null;
  "volser_pattern"?: string | null;
  "gdg_retention"?: number | null;
  "protected_resources"?: Array<string>;
  "confidence_weight_overrides"?: Record<string, number>;
  "review"?: ReviewConfig;
}

export type RegionTier = "development" | "integration" | "qa" | "uat" | "production";

export interface RegionUpsertRequest {
  "profile": RegionProfile;
  "reason": string;
}

export interface RegionUpsertResponse {
  "name": string;
  "audit_event_id": string;
  "review_required": boolean;
}

export interface ReviewConfig {
  "auto_approve_threshold"?: number;
  "allowed_reviewers"?: Record<string, Array<string>>;
}

export type ReviewState = "draft" | "pending_review" | "approved" | "rejected" | "cancelled";

export type Role = "developer" | "reviewer" | "admin" | "service";

export interface Runbook {
  "id": string;
  "title": string;
  "applies_to": Array<AppliesTo>;
  "body_markdown": string;
  "fix_actions"?: Array<FixAction>;
  "created_by": string;
  "created_from_event_id"?: string | null;
  "success_count"?: number;
  "failure_count"?: number;
  "last_applied_at"?: string | null;
}

export interface RunbookApplyRequest {
  "event_id"?: string | null;
  "notes"?: string | null;
}

export interface RunbookApplyResponse {
  "runbook_id": string;
  "application_id": string;
}

export interface RunbookCreateRequest {
  "title": string;
  "applies_to": Array<AppliesTo>;
  "body_markdown": string;
  "fix_actions"?: Array<FixAction>;
}

export interface RunbookCreateResponse {
  "runbook": Runbook;
  "audit_event_id": string;
}

export interface RunbookListResponse {
  "runbooks": Array<Runbook>;
  "total": number;
}

export interface RunbookRankEntry {
  "runbook_id": string;
  "title": string;
  "success_count": number;
  "failure_count": number;
}

export interface RunbookRankResponse {
  "abend_code": string;
  "program"?: string | null;
  "runbooks": Array<RunbookRankEntry>;
}

export interface ScanRequest {
  "jcl_source"?: string | null;
  "jcl_name"?: string | null;
  "region"?: string | null;
  "target_region"?: string | null;
}

export interface ScanResponse {
  "findings": Array<Finding>;
  "scan_duration_ms"?: number;
}

export interface ScoreBreakdown {
  "base"?: number;
  "deductions"?: Record<string, number>;
  "boosts"?: Record<string, number>;
}

export interface ScoreOverrideRequest {
  "new_score": number;
  "reason": string;
}

export interface ScoreOverrideResponse {
  "event_id": string;
  "original_score": number;
  "new_score": number;
  "audit_event_id": string;
  "learning_event_id": string;
}

export interface ScoreRequest {
  "jcl_source"?: string | null;
  "jcl_name"?: string | null;
  "region": string;
}

export interface ScoreResponse {
  "score": number;
  "breakdown": ScoreBreakdown;
}

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export interface SourceTrace {
  "file"?: string | null;
  "line"?: number | null;
  "paragraph"?: string | null;
  "highlighted_field"?: string | null;
}

export interface StubMarker {
  "feature": string;
  "spec"?: string | null;
  "reserved_for"?: string;
}

export interface Subject {
  "kind": string;
  "name": string;
  "region"?: string | null;
}

export interface TimestampedDoc {
  "schema_version"?: string;
  "kind": string;
  "ts": string;
  "ts_unix_ms": number;
  "shop"?: string;
}

export interface UserDoc {
  "_id": string;
  "_rev"?: string | null;
  "schema_version"?: string;
  "kind"?: string;
  "shop"?: string;
  "email": string;
  "display_name": string;
  "roles": Array<Role>;
  "preferences"?: UserPreferences;
  "created_at": string;
  "last_login_at"?: string | null;
}

export interface UserPreferences {
  "default_region_view"?: string;
  "show_dissent_inline"?: boolean;
  "notify_on_review_decision"?: boolean;
}

export interface WeightsResponse {
  "region": string;
  "weights": Record<string, number>;
  "source": string;
}

export interface WeightsUpdateRequest {
  "weights": Record<string, number>;
  "reason": string;
}

export interface WeightsUpdateResponse {
  "region": string;
  "weights": Record<string, number>;
  "audit_event_id": string;
  "review_required": boolean;
}
