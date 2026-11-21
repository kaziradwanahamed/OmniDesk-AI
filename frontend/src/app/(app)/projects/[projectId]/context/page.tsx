"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { ListChecks, Pin } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/cn";
import {
  sampleDecisions,
  sampleInstructions,
  sampleProjects,
  sampleSummary,
  sampleTasks,
} from "@/lib/sample";
import type { TaskStatus } from "@/lib/types";

const TASK_TONE: Record<TaskStatus, string> = {
  todo: "text-tertiary",
  in_progress: "text-accent",
  done: "text-success",
  blocked: "text-danger",
};

export default function ContextPage() {
  const params = useParams<{ projectId: string }>();
  const project =
    sampleProjects.find((p) => p.id === params.projectId) ?? sampleProjects[0];

  const [instructions, setInstructions] = useState(sampleInstructions.content);
  const [style, setStyle] = useState(sampleInstructions.responseStyle ?? "");
  const [summary, setSummary] = useState(sampleSummary.text);

  return (
    <>
      <PageHeader title="Memory & Instructions" description={project.name} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Project Instructions</CardTitle>
                <Badge>v{sampleInstructions.version}</Badge>
              </div>
              <CardDescription>
                Injected into every turn, for every model.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                rows={4}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
              />
              <div>
                <label className="mb-1 block text-xs font-medium text-secondary">
                  Preferred response style
                </label>
                <Textarea
                  rows={2}
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                />
              </div>
              <div className="flex justify-end">
                <Button size="sm">Save instructions</Button>
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
                The active task is injected as the current focus.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {sampleTasks.map((t) => (
                <div
                  key={t.id}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-3 py-2",
                    t.isActive ? "border-accent/40 bg-accent/5" : "border-subtle",
                  )}
                >
                  <span
                    className={cn("h-2 w-2 rounded-full bg-current", TASK_TONE[t.status])}
                  />
                  <span className="flex-1 text-sm text-primary">{t.title}</span>
                  {t.isActive ? (
                    <Badge className="border-accent/40 text-accent">Active</Badge>
                  ) : null}
                  <span className="font-mono text-[11px] text-tertiary">
                    {t.status}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1.5">
                <Pin className="h-4 w-4" />
                Decisions
              </CardTitle>
              <CardDescription>
                Pinned so future models never contradict prior agreements.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {sampleDecisions.map((d) => (
                <div
                  key={d.id}
                  className="rounded-lg border border-subtle px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-primary">
                      {d.title}
                    </span>
                    <Badge
                      className={
                        d.status === "active"
                          ? "border-success/40 text-success"
                          : "border-subtle text-tertiary"
                      }
                    >
                      {d.status}
                    </Badge>
                  </div>
                  {d.rationale ? (
                    <p className="mt-0.5 text-xs text-tertiary">{d.rationale}</p>
                  ) : null}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Conversation Summary</CardTitle>
                <Badge>v{sampleSummary.version}</Badge>
              </div>
              <CardDescription>
                Older turns are summarized; raw history is kept immutably.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                rows={4}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <Button size="sm" variant="secondary">
                  Refresh
                </Button>
                <Button size="sm">Save</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
