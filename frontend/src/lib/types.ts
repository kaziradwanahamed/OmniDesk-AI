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
  systemPrompt: string;
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
