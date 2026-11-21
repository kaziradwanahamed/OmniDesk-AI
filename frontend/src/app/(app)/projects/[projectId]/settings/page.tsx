"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Check, Loader2, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/empty-state";
import { useProjects } from "@/components/projects/projects-provider";
import { api, ApiError } from "@/lib/api-client";
import type { ProjectInstructions, ProjectStatus } from "@/lib/types";

const STATUSES: ProjectStatus[] = ["active", "paused", "archived"];

export default function ProjectSettingsPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const router = useRouter();
  const { updateProjectLocal, removeProject } = useProjects();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Project fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [goals, setGoals] = useState("");
  const [techStack, setTechStack] = useState("");
  const [status, setStatus] = useState<ProjectStatus>("active");
  const [progressNotes, setProgressNotes] = useState("");

  // Instructions
  const [instructions, setInstructions] = useState<ProjectInstructions | null>(
    null,
  );
  const [content, setContent] = useState("");
  const [responseStyle, setResponseStyle] = useState("");

  const [savingProject, setSavingProject] = useState(false);
  const [savedProject, setSavedProject] = useState(false);
  const [savingInstructions, setSavingInstructions] = useState(false);
  const [savedInstructions, setSavedInstructions] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [project, ins] = await Promise.all([
          api.getProject(projectId),
          api.getInstructions(projectId),
        ]);
        if (!active) return;
        setName(project.name);
        setDescription(project.description ?? "");
        setGoals(project.goals ?? "");
        setTechStack(project.techStack ?? "");
        setStatus(project.status);
        setProgressNotes(project.progressNotes ?? "");
        setInstructions(ins);
        setContent(ins?.content ?? "");
        setResponseStyle(ins?.responseStyle ?? "");
      } catch (err) {
        if (active)
          setLoadError(
            err instanceof ApiError && err.status === 404
              ? "Project not found."
              : "Could not load this project.",
          );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  async function saveProject(e: React.FormEvent) {
    e.preventDefault();
    setSavingProject(true);
    setSavedProject(false);
    try {
      const updated = await api.updateProject(projectId, {
        name: name.trim(),
        description,
        goals,
        techStack,
        status,
        progressNotes,
      });
      updateProjectLocal(updated);
      setSavedProject(true);
      setTimeout(() => setSavedProject(false), 2000);
    } catch {
      /* surfaced inline below via disabled state; keep simple */
    } finally {
      setSavingProject(false);
    }
  }

  async function saveInstructions(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setSavingInstructions(true);
    setSavedInstructions(false);
    try {
      const updated = await api.updateInstructions(
        projectId,
        content,
        responseStyle || undefined,
      );
      setInstructions(updated);
      setSavedInstructions(true);
      setTimeout(() => setSavedInstructions(false), 2000);
    } catch {
      /* ignore */
    } finally {
      setSavingInstructions(false);
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      await api.deleteProject(projectId);
      removeProject(projectId);
      router.push("/projects");
    } catch {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <>
        <PageHeader title="Project settings" />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-tertiary" />
        </div>
      </>
    );
  }

  if (loadError) {
    return (
      <>
        <PageHeader title="Project settings" />
        <div className="mx-auto w-full max-w-3xl px-4 py-10">
          <EmptyState
            title={loadError}
            description="It may have been deleted, or you may not have access to it."
            action={
              <Button variant="secondary" onClick={() => router.push("/projects")}>
                Back to projects
              </Button>
            }
          />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title={name || "Project settings"} description="Overview & instructions" />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          {/* Project overview */}
          <Card>
            <CardHeader>
              <CardTitle>Project overview</CardTitle>
              <CardDescription>
                Name, description, goals, tech stack, and status.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={saveProject} className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-secondary">Name</label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-secondary">
                    Description
                  </label>
                  <Textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-secondary">Goals</label>
                  <Textarea
                    rows={2}
                    value={goals}
                    onChange={(e) => setGoals(e.target.value)}
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-secondary">
                      Tech stack
                    </label>
                    <Input
                      value={techStack}
                      onChange={(e) => setTechStack(e.target.value)}
                      placeholder="FastAPI · PostgreSQL"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-secondary">
                      Status
                    </label>
                    <select
                      value={status}
                      onChange={(e) =>
                        setStatus(e.target.value as ProjectStatus)
                      }
                      className="h-9 w-full rounded-md border border-subtle bg-canvas px-3 text-sm text-primary outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/30"
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-secondary">
                    Progress notes
                  </label>
                  <Textarea
                    rows={2}
                    value={progressNotes}
                    onChange={(e) => setProgressNotes(e.target.value)}
                  />
                </div>
                <div className="flex items-center justify-end gap-2">
                  {savedProject ? (
                    <span className="inline-flex items-center gap-1 text-xs text-success">
                      <Check className="h-3.5 w-3.5" />
                      Saved
                    </span>
                  ) : null}
                  <Button type="submit" size="sm" disabled={savingProject || !name.trim()}>
                    {savingProject ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Save overview
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Instructions */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Persistent instructions</CardTitle>
                {instructions ? (
                  <Badge>v{instructions.version}</Badge>
                ) : (
                  <Badge className="text-tertiary">none yet</Badge>
                )}
              </div>
              <CardDescription>
                Injected into every turn, for every model. Saving creates a new
                version.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={saveInstructions} className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-secondary">
                    Instructions
                  </label>
                  <Textarea
                    rows={4}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="e.g. Use FastAPI with strict zero-trust checks; concise, diff-ready code."
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-secondary">
                    Preferred response style
                  </label>
                  <Input
                    value={responseStyle}
                    onChange={(e) => setResponseStyle(e.target.value)}
                    placeholder="Concise, technical"
                  />
                </div>
                <div className="flex items-center justify-end gap-2">
                  {savedInstructions ? (
                    <span className="inline-flex items-center gap-1 text-xs text-success">
                      <Check className="h-3.5 w-3.5" />
                      Saved v{instructions?.version}
                    </span>
                  ) : null}
                  <Button
                    type="submit"
                    size="sm"
                    disabled={savingInstructions || !content.trim()}
                  >
                    {savingInstructions ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Save instructions
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Danger zone */}
          <Card className="border-danger/30">
            <CardHeader>
              <CardTitle className="text-danger">Danger zone</CardTitle>
              <CardDescription>
                Permanently delete this project and everything in it.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>
                <Trash2 className="h-3.5 w-3.5" />
                Delete project
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={deleteOpen} onOpenChange={(o) => !o && setDeleteOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete project?</DialogTitle>
            <DialogDescription>
              This permanently deletes{" "}
              <span className="font-medium text-primary">{name}</span> and all of
              its conversations, instructions, and memory. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => setDeleteOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
