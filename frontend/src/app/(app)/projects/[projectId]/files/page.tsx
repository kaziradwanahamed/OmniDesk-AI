"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  Download,
  FileText,
  Loader2,
  Pin,
  Trash2,
  Upload,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/shared/empty-state";
import { useProjects } from "@/components/projects/projects-provider";
import { api, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import type { Attachment } from "@/lib/types";

const ALLOWED = ".md,.txt,.py,.ts,.tsx,.json,.yaml,.yml,.sql,.csv,.pdf";

const STATUS_TONE: Record<string, string> = {
  extracted: "border-success/40 text-success",
  pending: "border-subtle text-tertiary",
  empty: "border-warning/40 text-warning",
  encrypted: "border-warning/40 text-warning",
  failed: "border-danger/40 text-danger",
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FilesPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const { projects } = useProjects();
  const project = projects.find((p) => p.id === projectId) ?? null;

  const [files, setFiles] = useState<Attachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await api.listFiles(projectId);
        if (active) setFiles(list);
      } catch (e) {
        if (active)
          setError(e instanceof ApiError ? e.message : "Could not load files.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  function mergeFile(f: Attachment) {
    setFiles((prev) => {
      const without = prev.filter((x) => x.id !== f.id);
      return [f, ...without];
    });
  }

  async function uploadFiles(list: FileList | File[]) {
    const picked = Array.from(list);
    if (!picked.length) return;
    setUploading(true);
    setError(null);
    setNotice(null);
    const failures: string[] = [];
    let deduped = 0;
    for (const file of picked) {
      try {
        const saved = await api.uploadFile(projectId, file);
        mergeFile(saved);
        if (saved.deduplicated) deduped += 1;
      } catch (e) {
        failures.push(
          `${file.name}: ${e instanceof ApiError ? e.message : "upload failed"}`,
        );
      }
    }
    setUploading(false);
    if (failures.length) setError(failures.join(" · "));
    if (deduped > 0)
      setNotice(`${deduped} file(s) already existed and were not duplicated.`);
  }

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) void uploadFiles(e.target.files);
    e.target.value = "";
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) void uploadFiles(e.dataTransfer.files);
  }

  async function togglePin(f: Attachment) {
    setBusyId(f.id);
    setError(null);
    try {
      const updated = await api.updateFile(projectId, f.id, { pinned: !f.pinned });
      setFiles((prev) => prev.map((x) => (x.id === f.id ? updated : x)));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not update file.");
    } finally {
      setBusyId(null);
    }
  }

  async function removeFile(f: Attachment) {
    if (!window.confirm(`Delete "${f.filename}"? This also removes its excerpts.`))
      return;
    setBusyId(f.id);
    setError(null);
    try {
      await api.deleteFile(projectId, f.id);
      setFiles((prev) => prev.filter((x) => x.id !== f.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not delete file.");
    } finally {
      setBusyId(null);
    }
  }

  async function exportProject(format: "md" | "json") {
    setError(null);
    try {
      await api.downloadExport(projectId, format);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Export failed.");
    }
  }

  return (
    <>
      <PageHeader
        title="Files"
        description={project?.name ?? ""}
        actions={
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="secondary">
                  <Download className="h-4 w-4" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => exportProject("md")}>
                  Markdown (.md)
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => exportProject("json")}>
                  JSON (.json)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              size="sm"
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Upload
            </Button>
          </div>
        }
      />
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ALLOWED}
        className="hidden"
        onChange={onPick}
      />

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          {error ? (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          ) : null}
          {notice ? (
            <div className="rounded-lg border border-info/30 bg-info/10 px-3 py-2 text-sm text-secondary">
              {notice}
            </div>
          ) : null}

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed px-4 py-8 text-center transition-colors",
              dragging
                ? "border-accent bg-accent/5"
                : "border-strong hover:border-accent/60",
            )}
          >
            <Upload className="h-5 w-5 text-tertiary" />
            <p className="text-sm font-medium text-primary">
              Drop files here or click to upload
            </p>
            <p className="text-xs text-tertiary">
              .md .txt .py .ts .tsx .json .yaml .sql .csv .pdf — up to 10 MB each
            </p>
          </div>

          {loading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-tertiary" />
            </div>
          ) : files.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No files yet"
              description="Upload specs, source files, or docs to ground responses in real content. Pin a file to always include it in context (layer 5)."
            />
          ) : (
            <Card className="divide-y divide-subtle">
              {files.map((f) => (
                <div key={f.id} className="flex items-center gap-3 px-3 py-2.5">
                  <FileText className="h-4 w-4 shrink-0 text-tertiary" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-primary">
                      {f.filename}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-tertiary">
                      <span className="font-mono uppercase">
                        {f.extension.replace(".", "") || "file"}
                      </span>
                      <span>· {formatBytes(f.sizeBytes)}</span>
                      <span>· {f.chunkCount} chunk{f.chunkCount === 1 ? "" : "s"}</span>
                      <Badge
                        className={STATUS_TONE[f.extractionStatus] ?? "border-subtle text-tertiary"}
                      >
                        {f.extractionStatus}
                      </Badge>
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label={f.pinned ? "Unpin from context" : "Pin to context"}
                    title={f.pinned ? "Pinned to context (L5)" : "Pin to context (L5)"}
                    disabled={busyId === f.id}
                    onClick={() => togglePin(f)}
                    className={cn(
                      "shrink-0 rounded p-1.5 transition-colors",
                      f.pinned
                        ? "text-accent"
                        : "text-tertiary hover:text-primary",
                    )}
                  >
                    <Pin
                      className="h-4 w-4"
                      fill={f.pinned ? "currentColor" : "none"}
                    />
                  </button>
                  <button
                    type="button"
                    aria-label="Delete file"
                    disabled={busyId === f.id}
                    onClick={() => removeFile(f)}
                    className="shrink-0 rounded p-1.5 text-tertiary transition-colors hover:text-danger"
                  >
                    {busyId === f.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              ))}
            </Card>
          )}

          <p className="px-1 text-xs text-tertiary">
            Pinned files are injected into every turn (context layer 5). Other files
            surface automatically when relevant to your message, ranked by
            PostgreSQL full-text search — never sent all at once.
          </p>
        </div>
      </div>
    </>
  );
}
