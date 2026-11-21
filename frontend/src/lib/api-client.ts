/**
 * Typed client for the OmniDesk FastAPI backend.
 *
 * - Sends cookies with every request (`credentials: "include"`) so the HttpOnly
 *   session cookie flows automatically.
 * - Echoes the double-submit CSRF token (read from the `csrf_token` cookie) as
 *   `X-CSRF-Token` on state-changing requests.
 * - Maps snake_case API DTOs to the camelCase UI types.
 *
 * The API base URL is a non-secret public value (NEXT_PUBLIC_API_BASE_URL).
 */

import type {
  AuthUser,
  Project,
  ProjectInstructions,
  ProjectStatus,
} from "./types";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000") + "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  }
  return `Request failed (${status})`;
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
  if (!res.ok) throw new ApiError(res.status, extractMessage(data, res.status));
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
};
