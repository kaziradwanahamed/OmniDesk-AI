/**
 * Typed client for the OmniDesk FastAPI backend.
 *
 * - Sends cookies with every request (`credentials: "include"`).
 * - Echoes the double-submit CSRF token (`csrf_token` cookie) as `X-CSRF-Token`
 *   on state-changing requests.
 * - Maps snake_case API DTOs to the camelCase UI types.
 *
 * The API base URL is a non-secret public value (NEXT_PUBLIC_API_BASE_URL).
 */

import type {
  AuthUser,
  ChatMessage,
  Conversation,
  ContextPreview,
  MessageRole,
  MessageStatus,
  Project,
  ProjectDecision,
  ProjectInstructions,
  ProjectStatus,
  ProjectTask,
  DecisionStatus,
  TaskStatus,
} from "./types";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000") + "/api/v1";

export class ApiError extends Error {
  status: number;
  category?: string;
  constructor(status: number, message: string, category?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.category = category;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name + "=([^;]*)"),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function extractMessage(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const d = data as { detail?: unknown; message?: unknown };
    if (typeof d.detail === "string") return d.detail;
    if (Array.isArray(d.detail) && d.detail.length) {
      const first = d.detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
    if (typeof d.message === "string") return d.message;
  }
  return `Request failed (${status})`;
}

function extractCategory(data: unknown): string | undefined {
  if (data && typeof data === "object" && "category" in data) {
    const c = (data as { category: unknown }).category;
    if (typeof c === "string") return c;
  }
  return undefined;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method)) {
    const csrf = readCookie("csrf_token");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers,
      credentials: "include",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    throw new ApiError(
      res.status,
      extractMessage(data, res.status),
      extractCategory(data),
    );
  }
  return data as T;
}

// --- API DTOs (snake_case) ---
interface ApiUser {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}
interface ApiProject {
  id: string;
  name: string;
  description: string | null;
  goals: string | null;
  tech_stack: string | null;
  status: string;
  progress_notes: string | null;
  created_at: string;
  updated_at: string;
}
interface ApiInstructions {
  id: string;
  content: string;
  response_style: string | null;
  version: number;
  is_active: boolean;
  updated_at: string;
}
interface ApiConversation {
  id: string;
  project_id: string;
  title: string;
  active_provider: string | null;
  active_model_id: string | null;
  created_at: string;
  updated_at: string;
}
interface ApiMessage {
  id: string;
  conversation_id: string;
  sequence_no: number;
  role: string;
  content: string;
  provider: string | null;
  model_id: string | null;
  status: string;
  error_code: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  latency_ms: number | null;
  provider_request_id: string | null;
  context_snapshot_id: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

function mapUser(u: ApiUser): AuthUser {
  return {
    id: u.id,
    email: u.email,
    displayName: u.display_name,
    createdAt: u.created_at,
  };
}

function mapProject(p: ApiProject): Project {
  return {
    id: p.id,
    name: p.name,
    description: p.description ?? "",
    goals: p.goals ?? undefined,
    techStack: p.tech_stack ?? undefined,
    status: p.status as ProjectStatus,
    progressNotes: p.progress_notes,
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  };
}

function mapInstructions(i: ApiInstructions | null): ProjectInstructions | null {
  if (!i) return null;
  return {
    content: i.content,
    responseStyle: i.response_style ?? undefined,
    version: i.version,
    updatedAt: i.updated_at,
  };
}

function mapConversation(c: ApiConversation): Conversation {
  return {
    id: c.id,
    projectId: c.project_id,
    title: c.title,
    activeProvider: c.active_provider,
    activeModelId: c.active_model_id,
    updatedAt: c.updated_at,
  };
}

function mapSwitchEvent(meta: Record<string, unknown> | null): ChatMessage["event"] {
  if (!meta || meta.event !== "model_switched") return null;
  const side = (v: unknown) => {
    if (!v || typeof v !== "object") return null;
    const o = v as { provider?: unknown; model_id?: unknown };
    return {
      provider: typeof o.provider === "string" ? o.provider : "",
      modelId: typeof o.model_id === "string" ? o.model_id : null,
    };
  };
  return {
    type: "model_switched",
    from: side(meta.from),
    to: side(meta.to),
  };
}

function mapMessage(m: ApiMessage): ChatMessage {
  return {
    id: m.id,
    role: m.role as MessageRole,
    content: m.content,
    provider: m.provider,
    modelId: m.model_id,
    status: m.status as MessageStatus,
    usage: {
      inputTokens: m.input_tokens,
      outputTokens: m.output_tokens,
      totalTokens: m.total_tokens,
    },
    latencyMs: m.latency_ms,
    contextSnapshotId: m.context_snapshot_id,
    event: m.role === "system_event" ? mapSwitchEvent(m.metadata_json) : null,
    createdAt: m.created_at,
  };
}

interface ApiProviderConfig {
  provider: string;
  configured: boolean;
  key_hint: string | null;
  enabled_models: string[];
  is_enabled: boolean;
}
interface ApiUsageSummary {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  by_model: {
    provider: string;
    model_id: string | null;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    request_count: number;
  }[];
}

export interface ProviderConfigUI {
  provider: string;
  configured: boolean;
  keyHint: string | null;
  enabledModels: string[];
  isEnabled: boolean;
}
export interface TestConnectionResult {
  ok: boolean;
  models: string[];
  category: string | null;
  message: string | null;
}
export interface UsageByModelUI {
  provider: string;
  modelId: string | null;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  requestCount: number;
}
export interface UsageSummaryUI {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  byModel: UsageByModelUI[];
}

function mapProviderConfig(c: ApiProviderConfig): ProviderConfigUI {
  return {
    provider: c.provider,
    configured: c.configured,
    keyHint: c.key_hint,
    enabledModels: c.enabled_models,
    isEnabled: c.is_enabled,
  };
}
function mapUsage(u: ApiUsageSummary): UsageSummaryUI {
  return {
    inputTokens: u.input_tokens,
    outputTokens: u.output_tokens,
    totalTokens: u.total_tokens,
    byModel: u.by_model.map((m) => ({
      provider: m.provider,
      modelId: m.model_id,
      inputTokens: m.input_tokens,
      outputTokens: m.output_tokens,
      totalTokens: m.total_tokens,
      requestCount: m.request_count,
    })),
  };
}

export interface ProjectInput {
  name?: string;
  description?: string;
  goals?: string;
  techStack?: string;
  status?: ProjectStatus;
  progressNotes?: string;
}

function toApiProjectBody(input: ProjectInput): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  if (input.name !== undefined) body.name = input.name;
  if (input.description !== undefined) body.description = input.description;
  if (input.goals !== undefined) body.goals = input.goals;
  if (input.techStack !== undefined) body.tech_stack = input.techStack;
  if (input.status !== undefined) body.status = input.status;
  if (input.progressNotes !== undefined) body.progress_notes = input.progressNotes;
  return body;
}

interface ApiDecision {
  id: string;
  project_id: string;
  title: string;
  rationale: string | null;
  status: string;
  source_message_id: string | null;
  created_at: string;
}
interface ApiTask {
  id: string;
  project_id: string;
  title: string;
  details: string | null;
  status: string;
  is_active_task: boolean;
  updated_at: string;
}
interface ApiContextPreview {
  target_provider: string;
  target_model_id: string;
  token_budget: number;
  estimated_input_tokens: number;
  included_layers: string[];
  omitted_items: Record<string, unknown>[];
  recent_message_count: number;
  system_prompt: string;
}

function mapDecision(d: ApiDecision): ProjectDecision {
  return {
    id: d.id,
    title: d.title,
    rationale: d.rationale ?? undefined,
    status: d.status as DecisionStatus,
    createdAt: d.created_at,
  };
}
function mapTask(t: ApiTask): ProjectTask {
  return {
    id: t.id,
    title: t.title,
    details: t.details ?? undefined,
    status: t.status as TaskStatus,
    isActive: t.is_active_task,
  };
}
function mapContextPreview(p: ApiContextPreview): ContextPreview {
  return {
    targetProvider: p.target_provider,
    targetModelId: p.target_model_id,
    tokenBudget: p.token_budget,
    estimatedInputTokens: p.estimated_input_tokens,
    includedLayers: p.included_layers,
    omittedItems: p.omitted_items,
    recentMessageCount: p.recent_message_count,
    systemPrompt: p.system_prompt,
  };
}

export const api = {
  // --- auth ---
  async register(
    email: string,
    password: string,
    displayName?: string,
  ): Promise<AuthUser> {
    return mapUser(
      await request<ApiUser>("POST", "/auth/register", {
        email,
        password,
        display_name: displayName ?? null,
      }),
    );
  },
  async login(email: string, password: string): Promise<AuthUser> {
    return mapUser(
      await request<ApiUser>("POST", "/auth/login", { email, password }),
    );
  },
  async logout(): Promise<void> {
    await request<void>("POST", "/auth/logout");
  },
  async me(): Promise<AuthUser> {
    return mapUser(await request<ApiUser>("GET", "/auth/me"));
  },

  // --- projects ---
  async listProjects(): Promise<Project[]> {
    return (await request<ApiProject[]>("GET", "/projects")).map(mapProject);
  },
  async createProject(input: ProjectInput): Promise<Project> {
    return mapProject(
      await request<ApiProject>("POST", "/projects", toApiProjectBody(input)),
    );
  },
  async getProject(id: string): Promise<Project> {
    return mapProject(await request<ApiProject>("GET", `/projects/${id}`));
  },
  async updateProject(id: string, input: ProjectInput): Promise<Project> {
    return mapProject(
      await request<ApiProject>(
        "PATCH",
        `/projects/${id}`,
        toApiProjectBody(input),
      ),
    );
  },
  async deleteProject(id: string): Promise<void> {
    await request<void>("DELETE", `/projects/${id}`);
  },
  async getInstructions(id: string): Promise<ProjectInstructions | null> {
    return mapInstructions(
      await request<ApiInstructions | null>("GET", `/projects/${id}/instructions`),
    );
  },
  async updateInstructions(
    id: string,
    content: string,
    responseStyle?: string,
  ): Promise<ProjectInstructions> {
    const result = mapInstructions(
      await request<ApiInstructions>("PUT", `/projects/${id}/instructions`, {
        content,
        response_style: responseStyle ?? null,
      }),
    );
    return result as ProjectInstructions;
  },

  // --- conversations & messages ---
  async listConversations(projectId: string): Promise<Conversation[]> {
    return (
      await request<ApiConversation[]>(
        "GET",
        `/projects/${projectId}/conversations`,
      )
    ).map(mapConversation);
  },
  async createConversation(projectId: string, title: string): Promise<Conversation> {
    return mapConversation(
      await request<ApiConversation>(
        "POST",
        `/projects/${projectId}/conversations`,
        { title },
      ),
    );
  },
  async getConversation(id: string): Promise<Conversation> {
    return mapConversation(
      await request<ApiConversation>("GET", `/conversations/${id}`),
    );
  },
  async renameConversation(id: string, title: string): Promise<Conversation> {
    return mapConversation(
      await request<ApiConversation>("PATCH", `/conversations/${id}`, { title }),
    );
  },
  async deleteConversation(id: string): Promise<void> {
    await request<void>("DELETE", `/conversations/${id}`);
  },
  async getMessages(id: string): Promise<ChatMessage[]> {
    return (
      await request<ApiMessage[]>("GET", `/conversations/${id}/messages`)
    ).map(mapMessage);
  },
  async sendMessage(
    id: string,
    content: string,
    provider?: string,
    modelId?: string,
    retryMessageId?: string,
  ): Promise<{ userMessage: ChatMessage; assistantMessage: ChatMessage }> {
    const res = await request<{
      user_message: ApiMessage;
      assistant_message: ApiMessage;
    }>("POST", `/conversations/${id}/messages`, {
      content,
      provider: provider ?? null,
      model_id: modelId ?? null,
      retry_message_id: retryMessageId ?? null,
    });
    return {
      userMessage: mapMessage(res.user_message),
      assistantMessage: mapMessage(res.assistant_message),
    };
  },

  // --- project memory (decisions & tasks) ---
  async listDecisions(projectId: string): Promise<ProjectDecision[]> {
    return (
      await request<ApiDecision[]>("GET", `/projects/${projectId}/decisions`)
    ).map(mapDecision);
  },
  async createDecision(
    projectId: string,
    title: string,
    rationale?: string,
  ): Promise<ProjectDecision> {
    return mapDecision(
      await request<ApiDecision>("POST", `/projects/${projectId}/decisions`, {
        title,
        rationale: rationale ?? null,
      }),
    );
  },
  async updateDecision(
    projectId: string,
    decisionId: string,
    patch: { title?: string; rationale?: string; status?: DecisionStatus },
  ): Promise<ProjectDecision> {
    return mapDecision(
      await request<ApiDecision>(
        "PATCH",
        `/projects/${projectId}/decisions/${decisionId}`,
        patch,
      ),
    );
  },
  async deleteDecision(projectId: string, decisionId: string): Promise<void> {
    await request<void>(
      "DELETE",
      `/projects/${projectId}/decisions/${decisionId}`,
    );
  },
  async listTasks(projectId: string): Promise<ProjectTask[]> {
    return (
      await request<ApiTask[]>("GET", `/projects/${projectId}/tasks`)
    ).map(mapTask);
  },
  async createTask(
    projectId: string,
    title: string,
    details?: string,
  ): Promise<ProjectTask> {
    return mapTask(
      await request<ApiTask>("POST", `/projects/${projectId}/tasks`, {
        title,
        details: details ?? null,
      }),
    );
  },
  async updateTask(
    projectId: string,
    taskId: string,
    patch: { title?: string; details?: string; status?: TaskStatus },
  ): Promise<ProjectTask> {
    return mapTask(
      await request<ApiTask>(
        "PATCH",
        `/projects/${projectId}/tasks/${taskId}`,
        patch,
      ),
    );
  },
  async activateTask(projectId: string, taskId: string): Promise<ProjectTask> {
    return mapTask(
      await request<ApiTask>(
        "PATCH",
        `/projects/${projectId}/tasks/${taskId}/activate`,
      ),
    );
  },
  async deleteTask(projectId: string, taskId: string): Promise<void> {
    await request<void>("DELETE", `/projects/${projectId}/tasks/${taskId}`);
  },

  // --- context inspector & seamless model switching ---
  async getContextPreview(conversationId: string): Promise<ContextPreview> {
    return mapContextPreview(
      await request<ApiContextPreview>(
        "GET",
        `/conversations/${conversationId}/context-preview`,
      ),
    );
  },
  async switchModel(
    conversationId: string,
    provider: string,
    modelId: string,
  ): Promise<{ conversation: Conversation; event: ChatMessage | null }> {
    const res = await request<{
      conversation: ApiConversation;
      event: ApiMessage | null;
    }>("PATCH", `/conversations/${conversationId}/model`, {
      provider,
      model_id: modelId,
    });
    return {
      conversation: mapConversation(res.conversation),
      event: res.event ? mapMessage(res.event) : null,
    };
  },

  // --- providers & usage ---
  async listProviders(): Promise<ProviderConfigUI[]> {
    return (await request<ApiProviderConfig[]>("GET", "/providers")).map(
      mapProviderConfig,
    );
  },
  async setProviderKey(
    provider: string,
    apiKey: string,
  ): Promise<ProviderConfigUI> {
    return mapProviderConfig(
      await request<ApiProviderConfig>("PUT", `/providers/${provider}/key`, {
        api_key: apiKey,
      }),
    );
  },
  async deleteProviderKey(provider: string): Promise<ProviderConfigUI> {
    return mapProviderConfig(
      await request<ApiProviderConfig>("DELETE", `/providers/${provider}/key`),
    );
  },
  async testProvider(provider: string): Promise<TestConnectionResult> {
    return request<TestConnectionResult>("POST", `/providers/${provider}/test`);
  },
  async setEnabledModels(
    provider: string,
    models: string[],
  ): Promise<ProviderConfigUI> {
    return mapProviderConfig(
      await request<ApiProviderConfig>("PUT", `/providers/${provider}/models`, {
        enabled_models: models,
      }),
    );
  },
  async getUsage(): Promise<UsageSummaryUI> {
    return mapUsage(await request<ApiUsageSummary>("GET", "/usage"));
  },
};
