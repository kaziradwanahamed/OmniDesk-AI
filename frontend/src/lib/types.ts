/**
 * Front-end types mirroring the planned backend (Pydantic v2) DTOs from the
 * Implementation Blueprint. These drive the presentational UI; each screen is
 * wired to the real API as its backend phase lands. No model IDs, pricing, or
 * quotas are hardcoded here — those come from the backend / provider config.
 */

export type Provider = "openai" | "anthropic" | "gemini";

export type MessageRole = "user" | "assistant" | "system_event";
export type MessageStatus = "completed" | "streaming" | "failed";

export interface NormalizedUsage {
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
}

export interface ProviderModel {
  provider: Provider;
  /** Real model identifier supplied by the backend provider config. */
  modelId: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** Provider label — a known Provider, the "stub" adapter, etc. */
  provider?: string | null;
  modelId?: string | null;
  status?: MessageStatus;
  usage?: NormalizedUsage | null;
  latencyMs?: number | null;
  createdAt: string;
  /** Links an assistant turn to the auditable context snapshot it was sent with. */
  contextSnapshotId?: string | null;
  /** Set on parallel multi-model responses + their critiques/syntheses. */
  groupId?: string | null;
  /** Provenance for derived (critique/synthesis) messages. */
  metadata?: Record<string, unknown> | null;
  /** Present on system_event rows (e.g. a mid-conversation model switch).
   * `provider` is a free string ("stub" and future adapters are shown honestly). */
  event?: {
    type: "model_switched";
    from?: { provider: string; modelId: string | null } | null;
    to?: { provider: string; modelId: string | null } | null;
  } | null;
}

export interface Conversation {
  id: string;
  projectId: string;
  title: string;
  activeProvider: string | null;
  activeModelId: string | null;
  updatedAt: string;
  messageCount?: number;
}

export type ProjectStatus = "active" | "paused" | "archived";

export interface Project {
  id: string;
  name: string;
  description: string;
  goals?: string;
  techStack?: string;
  status: ProjectStatus;
  activeTask?: string | null;
  progressNotes?: string | null;
  createdAt?: string;
  updatedAt: string;
  conversationCount?: number;
}

/** Authenticated user (maps the backend UserOut DTO). */
export interface AuthUser {
  id: string;
  email: string;
  displayName: string | null;
  createdAt: string;
}

export interface ProjectInstructions {
  content: string;
  responseStyle?: string;
  version: number;
  updatedAt: string;
}

export type DecisionStatus = "active" | "superseded";
export interface ProjectDecision {
  id: string;
  title: string;
  rationale?: string;
  status: DecisionStatus;
  createdAt: string;
}

export type TaskStatus = "todo" | "in_progress" | "done" | "blocked";
export interface ProjectTask {
  id: string;
  title: string;
  details?: string;
  status: TaskStatus;
  isActive: boolean;
}

export interface ConversationSummary {
  version: number;
  coversUpToSequence: number;
  text: string;
  userEdited: boolean;
  updatedAt: string;
}

export interface ContextLayer {
  key: string;
  label: string;
  tokens: number;
  trimmed?: boolean;
}

export interface ContextSnapshot {
  targetProvider: Provider;
  targetModelId: string | null;
  tokenBudget: number;
  estimatedInputTokens: number;
  includedLayers: ContextLayer[];
  omittedItems: string[];
}

/** Dry-run of the backend 8-layer ContextBuilder for the next turn. */
export interface ContextPreview {
  targetProvider: string;
  targetModelId: string;
  tokenBudget: number;
  estimatedInputTokens: number;
  /** Layer tokens from the backend audit, e.g. "system", "decisions:3". */
  includedLayers: string[];
  /** Per-layer estimated token counts keyed by the included-layer name. */
  layerTokens: Record<string, number>;
  omittedItems: Array<Record<string, unknown>>;
  recentMessageCount: number;
  /** Layer-5 file excerpts injected into the next turn (pinned + query-matched). */
  fileExcerpts: FileExcerpt[];
  systemPrompt: string;
}

/** A project file (attachment) and its extraction/retrieval metadata. */
export interface Attachment {
  id: string;
  projectId: string;
  filename: string;
  extension: string;
  mimeType: string;
  sizeBytes: number;
  sha256: string;
  /** pending | extracted | empty | encrypted | failed */
  extractionStatus: string;
  extractionError?: string | null;
  chunkCount: number;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
  /** True when an identical file already existed and was returned on upload. */
  deduplicated?: boolean;
}

/** One Layer-5 excerpt surfaced in the Context Inspector (no file body). */
export interface FileExcerpt {
  filename: string;
  chunkIndex: number;
  tokenEst: number;
  pinned: boolean;
  matched: boolean;
  rank: number | null;
}

/** The active rolling conversation summary (L6), from the summary endpoints. */
export interface Summary {
  id: string;
  conversationId: string;
  version: number;
  coversUpToSequence: number;
  coveredMessageCount: number;
  content: string;
  estimatedTokens: number;
  provider: string | null;
  modelId: string | null;
  userEdited: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SummaryStatus {
  summary: Summary | null;
  unsummarizedCount: number;
  triggerThreshold: number;
  needsSummary: boolean;
}

/** A multi-model parallel-response group. */
export interface MessageGroupInfo {
  id: string;
  conversationId: string;
  userMessageId: string | null;
  selectedMessageId: string | null;
  kind: string;
  createdAt: string;
}

export interface MultiTarget {
  provider: string;
  modelId: string;
}

export interface MultiResponse {
  provider: string;
  modelId: string;
  message: ChatMessage | null;
  error: { category: string; message: string } | null;
}

export interface MultiSendResult {
  group: MessageGroupInfo;
  userMessage: ChatMessage;
  responses: MultiResponse[];
}

export interface DerivedResult {
  message: ChatMessage;
  group: MessageGroupInfo | null;
}

export type ProviderErrorCategory =
  | "AUTH_INVALID_KEY"
  | "RATE_LIMITED"
  | "QUOTA_EXCEEDED"
  | "BILLING_REQUIRED"
  | "CONTEXT_TOO_LARGE"
  | "MODEL_UNAVAILABLE"
  | "TIMEOUT";

export interface ProviderError {
  category: ProviderErrorCategory;
  message: string;
  retryAfterSeconds?: number | null;
}

export type ConnectionStatus = "connected" | "untested" | "invalid" | "testing";

export interface ProviderConfig {
  provider: Provider;
  /** Whether an API key is saved server-side. The key itself is never sent to the client. */
  configured: boolean;
  keyHint?: string | null;
  connection: ConnectionStatus;
  /** Enabled model IDs from the backend; empty until the user configures them. */
  enabledModels: string[];
  isEnabled: boolean;
}

export interface UsageRow {
  provider: Provider;
  modelId: string | null;
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  /** null renders as "N/A" — never fabricate a cost. */
  estimatedCostUsd: number | null;
}
