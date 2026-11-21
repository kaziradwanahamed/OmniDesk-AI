"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ListChecks,
  Loader2,
  Pin,
  Plus,
  Star,
  Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useProjects } from "@/components/projects/projects-provider";
import { api, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import type {
  ProjectDecision,
  ProjectTask,
  TaskStatus,
} from "@/lib/types";

const TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "done", "blocked"];
const TASK_TONE: Record<TaskStatus, string> = {
  todo: "text-tertiary",
  in_progress: "text-accent",
  done: "text-success",
  blocked: "text-danger",
};

export default function ContextPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const { projects } = useProjects();
  const project = projects.find((p) => p.id === projectId) ?? null;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [instructions, setInstructions] = useState("");
  const [style, setStyle] = useState("");
  const [instrVersion, setInstrVersion] = useState<number | null>(null);
  const [savingInstr, setSavingInstr] = useState(false);
  const [savedInstr, setSavedInstr] = useState(false);

  const [decisions, setDecisions] = useState<ProjectDecision[]>([]);
  const [tasks, setTasks] = useState<ProjectTask[]>([]);
  const [newTask, setNewTask] = useState("");
  const [newDecision, setNewDecision] = useState("");
  const [newRationale, setNewRationale] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [instr, decs, tks] = await Promise.all([
          api.getInstructions(projectId),
          api.listDecisions(projectId),
          api.listTasks(projectId),
        ]);
        if (!active) return;
        setInstructions(instr?.content ?? "");
        setStyle(instr?.responseStyle ?? "");
        setInstrVersion(instr?.version ?? null);
        setDecisions(decs);
        setTasks(tks);
      } catch (e) {
        if (active)
          setError(
            e instanceof ApiError ? e.message : "Could not load project memory.",
          );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  async function mutate(fn: () => Promise<void>) {
    try {
      await fn();
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Action failed.");
    }
  }

  async function saveInstructions() {
    setSavingInstr(true);
    setSavedInstr(false);
    try {
      const saved = await api.updateInstructions(
        projectId,
        instructions,
        style || undefined,
      );
      setInstrVersion(saved.version);
      setSavedInstr(true);
      setTimeout(() => setSavedInstr(false), 2000);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save instructions.");
    } finally {
      setSavingInstr(false);
    }
  }

  const addTask = () =>
    mutate(async () => {
      const title = newTask.trim();
      if (!title) return;
      const t = await api.createTask(projectId, title);
      setTasks((prev) => [...prev, t]);
      setNewTask("");
    });

  const activateTask = (task: ProjectTask) =>
    mutate(async () => {
      await api.activateTask(projectId, task.id);
      setTasks((prev) => prev.map((x) => ({ ...x, isActive: x.id === task.id })));
    });

  const cycleTaskStatus = (task: ProjectTask) =>
    mutate(async () => {
      const next =
        TASK_STATUSES[(TASK_STATUSES.indexOf(task.status) + 1) % TASK_STATUSES.length];
      const updated = await api.updateTask(projectId, task.id, { status: next });
      setTasks((prev) => prev.map((x) => (x.id === task.id ? updated : x)));
    });

  const removeTask = (task: ProjectTask) =>
    mutate(async () => {
      await api.deleteTask(projectId, task.id);
      setTasks((prev) => prev.filter((x) => x.id !== task.id));
    });

  const addDecision = () =>
    mutate(async () => {
      const title = newDecision.trim();
      if (!title) return;
      const d = await api.createDecision(
        projectId,
        title,
        newRationale.trim() || undefined,
      );
      setDecisions((prev) => [...prev, d]);
      setNewDecision("");
      setNewRationale("");
    });

  const toggleDecision = (d: ProjectDecision) =>
    mutate(async () => {
      const status = d.status === "active" ? "superseded" : "active";
      const updated = await api.updateDecision(projectId, d.id, { status });
      setDecisions((prev) => prev.map((x) => (x.id === d.id ? updated : x)));
    });

  const removeDecision = (d: ProjectDecision) =>
    mutate(async () => {
      await api.deleteDecision(projectId, d.id);
      setDecisions((prev) => prev.filter((x) => x.id !== d.id));
    });

  return (
    <>
      <PageHeader title="Memory & Instructions" description={project?.name ?? ""} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          {error ? (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-tertiary" />
            </div>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Project Instructions</CardTitle>
                    {instrVersion ? <Badge>v{instrVersion}</Badge> : null}
                  </div>
                  <CardDescription>
                    Injected into every turn, for every model (context layer 2).
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Textarea
                    rows={4}
                    value={instructions}
                    placeholder="Describe the project, conventions, and constraints every model should follow."
                    onChange={(e) => setInstructions(e.target.value)}
                  />
                  <div>
                    <label className="mb-1 block text-xs font-medium text-secondary">
                      Preferred response style
                    </label>
                    <Textarea
                      rows={2}
                      value={style}
                      placeholder="e.g. Concise, technical, with runnable code where useful."
                      onChange={(e) => setStyle(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-end gap-2">
                    {savedInstr ? (
                      <span className="text-xs text-success">Saved</span>
                    ) : null}
                    <Button
                      size="sm"
                      onClick={saveInstructions}
                      disabled={savingInstr || !instructions.trim()}
                    >
                      {savingInstr ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : null}
                      Save instructions
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-1.5">
                    <ListChecks className="h-4 w-4" />
                    Tasks
                  </CardTitle>
                  <CardDescription>
                    The active task is pinned as the current focus (context layer 3).
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {tasks.length === 0 ? (
                    <p className="text-sm text-tertiary">No tasks yet.</p>
                  ) : null}
                  {tasks.map((t) => (
                    <div
                      key={t.id}
                      className={cn(
                        "flex items-center gap-2 rounded-lg border px-3 py-2",
                        t.isActive ? "border-accent/40 bg-accent/5" : "border-subtle",
                      )}
                    >
                      <button
                        type="button"
                        aria-label={t.isActive ? "Active task" : "Set as active task"}
                        onClick={() => activateTask(t)}
                        className={cn(
                          "shrink-0 rounded p-0.5 transition-colors",
                          t.isActive
                            ? "text-accent"
                            : "text-tertiary hover:text-primary",
                        )}
                      >
                        <Star
                          className="h-4 w-4"
                          fill={t.isActive ? "currentColor" : "none"}
                        />
                      </button>
                      <span className="flex-1 text-sm text-primary">{t.title}</span>
                      {t.isActive ? (
                        <Badge className="border-accent/40 text-accent">Active</Badge>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => cycleTaskStatus(t)}
                        title="Cycle status"
                        className={cn(
                          "rounded px-1.5 py-0.5 font-mono text-[11px] transition-colors hover:bg-surface",
                          TASK_TONE[t.status],
                        )}
                      >
                        {t.status}
                      </button>
                      <button
                        type="button"
                        aria-label="Delete task"
                        onClick={() => removeTask(t)}
                        className="rounded p-1 text-tertiary transition-colors hover:text-danger"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 pt-1">
                    <Input
                      value={newTask}
                      placeholder="Add a task…"
                      onChange={(e) => setNewTask(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") addTask();
                      }}
                    />
                    <Button size="sm" onClick={addTask} disabled={!newTask.trim()}>
                      <Plus className="h-4 w-4" />
                      Add
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-1.5">
                    <Pin className="h-4 w-4" />
                    Decisions
                  </CardTitle>
                  <CardDescription>
                    Active decisions are pinned so future models never contradict
                    prior agreements (context layer 4).
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {decisions.length === 0 ? (
                    <p className="text-sm text-tertiary">No decisions recorded yet.</p>
                  ) : null}
                  {decisions.map((d) => (
                    <div
                      key={d.id}
                      className="rounded-lg border border-subtle px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-primary">
                          {d.title}
                        </span>
                        <div className="flex shrink-0 items-center gap-1">
                          <button
                            type="button"
                            onClick={() => toggleDecision(d)}
                            title="Toggle active / superseded"
                          >
                            <Badge
                              className={
                                d.status === "active"
                                  ? "border-success/40 text-success"
                                  : "border-subtle text-tertiary"
                              }
                            >
                              {d.status}
                            </Badge>
                          </button>
                          <button
                            type="button"
                            aria-label="Delete decision"
                            onClick={() => removeDecision(d)}
                            className="rounded p-1 text-tertiary transition-colors hover:text-danger"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                      {d.rationale ? (
                        <p className="mt-0.5 text-xs text-tertiary">{d.rationale}</p>
                      ) : null}
                    </div>
                  ))}
                  <div className="space-y-2 pt-1">
                    <Input
                      value={newDecision}
                      placeholder="Decision title…"
                      onChange={(e) => setNewDecision(e.target.value)}
                    />
                    <div className="flex items-center gap-2">
                      <Input
                        value={newRationale}
                        placeholder="Rationale (optional)"
                        onChange={(e) => setNewRationale(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") addDecision();
                        }}
                      />
                      <Button
                        size="sm"
                        onClick={addDecision}
                        disabled={!newDecision.trim()}
                      >
                        <Plus className="h-4 w-4" />
                        Add
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <p className="px-1 text-xs text-tertiary">
                Rolling conversation summaries (context layer 6) arrive in Phase 7;
                raw history is always kept immutably.
              </p>
            </>
          )}
        </div>
      </div>
    </>
  );
}
