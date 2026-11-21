/**
 * Illustrative PREVIEW fixtures for the presentational UI build.
 *
 * This is clearly-labeled sample content so every screen is navigable and the
 * design can be evaluated before the backend exists. It deliberately avoids
 * fabricating anything that must be real: model IDs are the obvious placeholder
 * "preview-model", provider settings default to an unconfigured state, and the
 * usage ledger is empty (costs render as "N/A"). Each screen swaps these for
 * typed API data as its backend phase (2–9) lands.
 */

import type {
  ChatMessage,
  Conversation,
  ConversationSummary,
  ContextSnapshot,
  Project,
  ProjectDecision,
  ProjectInstructions,
  ProjectTask,
  Provider,
  ProviderConfig,
} from "./types";

export const PREVIEW_NOTICE =
  "Preview — illustrative sample content. Not connected to a live backend yet.";

/** Placeholder model IDs per provider (never real identifiers). */
export const PREVIEW_MODELS: Record<Provider, string[]> = {
  openai: ["preview-model"],
  anthropic: ["preview-model"],
  gemini: ["preview-model"],
};

export const sampleProjects: Project[] = [
  {
    id: "p_sentinelgate",
    name: "SentinelGate AI",
    description:
      "Runtime security gateway for autonomous AI agents — per-request auth, rate limiting, and policy enforcement in front of a model router.",
    goals: "Ship a zero-trust FastAPI gateway with deterministic policy checks.",
    techStack: "FastAPI · PostgreSQL · Redis",
    status: "active",
    activeTask: "Harden the rate limiter for burst traffic",
    updatedAt: "2026-11-21T10:30:00.000Z",
    conversationCount: 3,
  },
  {
    id: "p_atlas",
    name: "Atlas Docs Pipeline",
    description:
      "Ingestion + retrieval pipeline for internal engineering documentation.",
    techStack: "Python · pgvector",
    status: "paused",
    activeTask: null,
    updatedAt: "2026-11-19T16:12:00.000Z",
    conversationCount: 1,
  },
];

export const sampleConversations: Conversation[] = [
  {
    id: "c_gateway",
    projectId: "p_sentinelgate",
    title: "Gateway middleware design",
    activeProvider: "anthropic",
    activeModelId: "preview-model",
    updatedAt: "2026-11-21T10:30:00.000Z",
    messageCount: 5,
  },
  {
    id: "c_ratelimit",
    projectId: "p_sentinelgate",
    title: "Rate limiter trade-offs",
    activeProvider: "openai",
    activeModelId: "preview-model",
    updatedAt: "2026-11-20T09:05:00.000Z",
    messageCount: 8,
  },
  {
    id: "c_schema",
    projectId: "p_sentinelgate",
    title: "Policy schema & migrations",
    activeProvider: "gemini",
    activeModelId: "preview-model",
    updatedAt: "2026-11-18T14:40:00.000Z",
    messageCount: 4,
  },
];

export const sampleMessages: ChatMessage[] = [
  {
    id: "m1",
    role: "user",
    content:
      "Let's design the FastAPI gateway for SentinelGate AI. I want strict per-request auth and rate limiting *before* anything reaches the model router.",
    createdAt: "2026-11-21T09:58:00.000Z",
  },
  {
    id: "m2",
    role: "assistant",
    provider: "openai",
    modelId: "preview-model",
    status: "completed",
    createdAt: "2026-11-21T09:58:30.000Z",
    usage: { inputTokens: 1240, outputTokens: 320, totalTokens: 1560 },
    latencyMs: 2100,
    content: `Here's a clean middleware ordering for the gateway:

1. **Auth** — validate the request token first; reject before any work.
2. **Rate limit** — per-principal token bucket keyed in Redis.
3. **Policy** — deterministic allow/deny checks.
4. **Route** — only then hand off to the model router.

\`\`\`python
@app.middleware("http")
async def gateway(request: Request, call_next):
    principal = await authenticate(request)      # 1. auth
    await rate_limiter.check(principal)           # 2. rate limit
    await policy.enforce(principal, request)      # 3. policy
    return await call_next(request)               # 4. route
\`\`\`

Keeping these ordered means a rejected request never consumes model budget.`,
  },
  {
    id: "m3",
    role: "system_event",
    createdAt: "2026-11-21T10:05:00.000Z",
    event: {
      type: "model_switched",
      from: { provider: "openai", modelId: "preview-model" },
      to: { provider: "anthropic", modelId: "preview-model" },
    },
    content: "",
  },
  {
    id: "m4",
    role: "user",
    content:
      "Good. Now harden the rate limiter for burst traffic and explain the trade-offs between token bucket and sliding window.",
    createdAt: "2026-11-21T10:06:00.000Z",
  },
  {
    id: "m5",
    role: "assistant",
    provider: "anthropic",
    modelId: "preview-model",
    status: "completed",
    createdAt: "2026-11-21T10:06:40.000Z",
    usage: { inputTokens: 1890, outputTokens: 540, totalTokens: 2430 },
    latencyMs: 3050,
    content: `Both approaches have clear trade-offs for burst handling:

| Algorithm | Burst behavior | Memory | Best for |
| --- | --- | --- | --- |
| Token bucket | Allows controlled bursts up to capacity | Low (2 fields) | API gateways |
| Sliding window | Smooths spikes, stricter | Higher (log) | Billing-sensitive limits |

For SentinelGate I'd use a **token bucket** with a small burst allowance, then fall back to a sliding-window counter for the per-minute hard cap. This absorbs legitimate bursts without letting a client sustain an overrun.`,
  },
];

export const sampleInstructions: ProjectInstructions = {
  content:
    "SentinelGate AI uses FastAPI with strict zero-trust policy checks. Prefer concise, diff-ready code. Always put auth and rate limiting before the model router.",
  responseStyle: "Concise, technical, with runnable code where useful.",
  version: 3,
  updatedAt: "2026-11-21T08:00:00.000Z",
};

export const sampleDecisions: ProjectDecision[] = [
  {
    id: "d1",
    title: "Gateway owns auth, rate limit, and policy before routing",
    rationale: "A rejected request must never consume model budget.",
    status: "active",
    createdAt: "2026-11-20T12:00:00.000Z",
  },
  {
    id: "d2",
    title: "Redis-backed token bucket for per-principal limits",
    status: "active",
    createdAt: "2026-11-20T12:30:00.000Z",
  },
  {
    id: "d3",
    title: "Use in-process cache for policy lookups",
    rationale: "Superseded by Redis for multi-worker consistency.",
    status: "superseded",
    createdAt: "2026-11-18T10:00:00.000Z",
  },
];

export const sampleTasks: ProjectTask[] = [
  {
    id: "t1",
    title: "Harden the rate limiter for burst traffic",
    status: "in_progress",
    isActive: true,
  },
  { id: "t2", title: "Add policy schema migration", status: "todo", isActive: false },
  {
    id: "t3",
    title: "Define canonical middleware ordering",
    status: "done",
    isActive: false,
  },
];

export const sampleSummary: ConversationSummary = {
  version: 2,
  coversUpToSequence: 2,
  text: "Established the gateway middleware ordering (auth → rate limit → policy → route) and agreed a rejected request must not consume model budget. Began hardening the rate limiter for burst traffic.",
  userEdited: false,
  updatedAt: "2026-11-21T10:06:00.000Z",
};

export const sampleSnapshot: ContextSnapshot = {
  targetProvider: "anthropic",
  targetModelId: "preview-model",
  tokenBudget: 16000,
  estimatedInputTokens: 3180,
  includedLayers: [
    { key: "system", label: "App system instructions", tokens: 180 },
    { key: "project_instructions", label: "Project instructions", tokens: 240 },
    { key: "active_task", label: "Active task", tokens: 60 },
    { key: "decisions", label: "Decisions (2)", tokens: 320 },
    { key: "summary", label: "Summary v2", tokens: 420 },
    { key: "recent_messages", label: "Recent messages (4)", tokens: 1960 },
  ],
  omittedItems: ["Older turns before summary v2", "File excerpt: architecture.md #3"],
};

/** Provider settings default to an honest unconfigured state. */
export function defaultProviderConfigs(): ProviderConfig[] {
  return [
    {
      provider: "openai",
      configured: false,
      keyHint: null,
      connection: "untested",
      enabledModels: [],
      isEnabled: true,
    },
    {
      provider: "anthropic",
      configured: false,
      keyHint: null,
      connection: "untested",
      enabledModels: [],
      isEnabled: true,
    },
    {
      provider: "gemini",
      configured: false,
      keyHint: null,
      connection: "untested",
      enabledModels: [],
      isEnabled: true,
    },
  ];
}
