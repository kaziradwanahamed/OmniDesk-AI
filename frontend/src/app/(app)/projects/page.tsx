"use client";

import { useState } from "react";
import Link from "next/link";
import {
  FolderPlus,
  Loader2,
  MoreVertical,
  Plus,
  Settings2,
  Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/shared/empty-state";
import { TimeAgo } from "@/components/shared/time-ago";
import { useProjects } from "@/components/projects/projects-provider";
import { api, ApiError } from "@/lib/api-client";
import type { Project, ProjectStatus } from "@/lib/types";

const STATUS_TONE: Record<ProjectStatus, string> = {
  active: "border-success/40 text-success",
  paused: "border-warning/40 text-warning",
  archived: "border-subtle text-tertiary",
};

export default function ProjectsPage() {
  const { projects, loading, error, addProject, removeProject, refresh } =
    useProjects();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function createProject(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const project = await api.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      addProject(project);
      setName("");
      setDescription("");
      setOpen(false);
    } catch (err) {
      setCreateError(
        err instanceof ApiError ? err.message : "Could not create project.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteProject(deleteTarget.id);
      removeProject(deleteTarget.id);
      setDeleteTarget(null);
    } catch {
      /* keep dialog open on failure */
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Projects"
        description="Your multi-model workspaces"
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4" />
                New project
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New project</DialogTitle>
                <DialogDescription>
                  Create a workspace with its own shared conversation and context.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={createProject} className="space-y-3">
                <div className="space-y-1.5">
                  <label htmlFor="pname" className="text-xs font-medium text-secondary">
                    Name
                  </label>
                  <Input
                    id="pname"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="SentinelGate AI"
                    disabled={creating}
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="pdesc" className="text-xs font-medium text-secondary">
                    Description
                  </label>
                  <Textarea
                    id="pdesc"
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What is this project about?"
                    disabled={creating}
                  />
                </div>
                {createError ? (
                  <p className="text-xs text-danger">{createError}</p>
                ) : null}
                <div className="flex justify-end gap-2 pt-1">
                  <DialogClose asChild>
                    <Button type="button" variant="ghost" disabled={creating}>
                      Cancel
                    </Button>
                  </DialogClose>
                  <Button type="submit" disabled={creating || !name.trim()}>
                    {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Create
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-4 py-6">
          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-40 w-full rounded-xl" />
              ))}
            </div>
          ) : error ? (
            <EmptyState
              icon={FolderPlus}
              title="Couldn't load projects"
              description={error}
              action={
                <Button variant="secondary" onClick={() => refresh()}>
                  Retry
                </Button>
              }
            />
          ) : projects.length ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((p) => (
                <Card
                  key={p.id}
                  className="flex flex-col p-4 transition-colors hover:border-strong"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h3 className="truncate font-semibold text-primary">
                      {p.name}
                    </h3>
                    <div className="flex items-center gap-1">
                      <Badge className={STATUS_TONE[p.status]}>{p.status}</Badge>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label="Project actions"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/projects/${p.id}/settings`}>
                              <Settings2 className="h-3.5 w-3.5" />
                              Project settings
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-danger focus:bg-danger/10"
                            onSelect={() => setDeleteTarget(p)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                  <p className="line-clamp-3 min-h-15 flex-1 text-sm text-secondary">
                    {p.description || "No description yet."}
                  </p>
                  <div className="mt-4 flex items-center justify-between">
                    <TimeAgo
                      iso={p.updatedAt}
                      className="text-xs text-tertiary"
                    />
                    <Button size="sm" variant="secondary" asChild>
                      <Link href={`/projects/${p.id}/settings`}>Open</Link>
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={FolderPlus}
              title="No projects yet"
              description="Create your first project to start a shared, model-switchable conversation."
              action={
                <Button onClick={() => setOpen(true)}>
                  <Plus className="h-4 w-4" />
                  New project
                </Button>
              }
            />
          )}
        </div>
      </div>

      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete project?</DialogTitle>
            <DialogDescription>
              This permanently deletes{" "}
              <span className="font-medium text-primary">
                {deleteTarget?.name}
              </span>{" "}
              and all of its conversations, instructions, and memory. This cannot
              be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => setDeleteTarget(null)}
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
