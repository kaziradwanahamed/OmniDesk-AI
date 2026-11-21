"use client";

import { useState } from "react";
import {
  FileText,
  ListChecks,
  Pencil,
  Pin,
  RefreshCw,
  Layers,
  Check,
} from "lucide-react";
import { TokenBudgetBar } from "./token-budget-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type {
  ContextSnapshot,
  ConversationSummary,
  ProjectDecision,
  ProjectInstructions,
  ProjectTask,
} from "@/lib/types";

function Section({
  icon: Icon,
  title,
  action,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-subtle px-4 py-4">
      <div className="mb-2.5 flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-tertiary uppercase">
          <Icon className="h-3.5 w-3.5" />
          {title}
        </h3>
        {action}
      </div>
      {children}
    </section>
  );
}

export function ContextInspector({
  instructions,
  activeTask,
  decisions,
  summary,
  snapshot,
}: {
  instructions: ProjectInstructions;
  activeTask?: ProjectTask | null;
  decisions: ProjectDecision[];
  summary: ConversationSummary;
  snapshot: ContextSnapshot;
}) {
  const [editingInstructions, setEditingInstructions] = useState(false);
  const [instructionsDraft, setInstructionsDraft] = useState(instructions.content);
  const [editingSummary, setEditingSummary] = useState(false);
  const [summaryDraft, setSummaryDraft] = useState(summary.text);

  const activeDecisions = decisions.filter((d) => d.status === "active");

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-subtle px-4 py-3.5">
        <h2 className="text-sm font-semibold text-primary">Context Included</h2>
        <p className="mt-0.5 text-xs text-secondary">
          Exactly what will be sent to the model on the next turn.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {/* Instructions & active task */}
        <Section
          icon={Pencil}
          title="Instructions & Active Task"
          action={
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label="Edit instructions"
              onClick={() => setEditingInstructions((v) => !v)}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
          }
        >
          {editingInstructions ? (
            <div className="space-y-2">
              <Textarea
                value={instructionsDraft}
                onChange={(e) => setInstructionsDraft(e.target.value)}
                rows={5}
              />
              <div className="flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setInstructionsDraft(instructions.content);
                    setEditingInstructions(false);
                  }}
                >
                  Cancel
                </Button>
                <Button size="sm" onClick={() => setEditingInstructions(false)}>
                  Save
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-secondary">
              {instructionsDraft}
            </p>
          )}
          {activeTask ? (
            <div className="mt-3 rounded-lg border border-accent/30 bg-accent/5 px-3 py-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-accent">
                <ListChecks className="h-3.5 w-3.5" />
                Active task
              </div>
              <p className="mt-0.5 text-sm text-primary">{activeTask.title}</p>
            </div>
          ) : null}
        </Section>

        {/* Decisions */}
        <Section icon={Pin} title={`Key Decisions (${activeDecisions.length})`}>
          {activeDecisions.length ? (
            <ul className="space-y-2">
              {activeDecisions.map((d) => (
                <li
                  key={d.id}
                  className="rounded-lg border border-subtle bg-canvas px-3 py-2"
                >
                  <p className="text-sm font-medium text-primary">{d.title}</p>
                  {d.rationale ? (
                    <p className="mt-0.5 text-xs text-tertiary">{d.rationale}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-tertiary">No pinned decisions yet.</p>
          )}
        </Section>

        {/* Summary */}
        <Section
          icon={Layers}
          title={`Summary (v${summary.version})`}
          action={
            <div className="flex items-center gap-1">
              <Button size="icon-sm" variant="ghost" aria-label="Refresh summary">
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label="Edit summary"
                onClick={() => setEditingSummary((v) => !v)}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            </div>
          }
        >
          {editingSummary ? (
            <div className="space-y-2">
              <Textarea
                value={summaryDraft}
                onChange={(e) => setSummaryDraft(e.target.value)}
                rows={5}
              />
              <div className="flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setSummaryDraft(summary.text);
                    setEditingSummary(false);
                  }}
                >
                  Cancel
                </Button>
                <Button size="sm" onClick={() => setEditingSummary(false)}>
                  Save
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-secondary">{summaryDraft}</p>
          )}
          <p className="mt-2 text-xs text-tertiary">
            Covers up to message #{summary.coversUpToSequence}. Raw history is
            kept immutably.
          </p>
        </Section>

        {/* Recent messages & token budget */}
        <Section icon={Layers} title="Token Budget">
          <TokenBudgetBar snapshot={snapshot} />
          <ul className="mt-3 space-y-1">
            {snapshot.includedLayers.map((layer) => (
              <li
                key={layer.key}
                className="flex items-center justify-between text-xs"
              >
                <span className="flex items-center gap-1.5 text-secondary">
                  <Check className="h-3 w-3 text-success" />
                  {layer.label}
                  {layer.trimmed ? (
                    <Badge className="ml-1 border-warning/40 text-warning">
                      trimmed
                    </Badge>
                  ) : null}
                </span>
                <span className="font-mono text-tertiary">{layer.tokens}</span>
              </li>
            ))}
          </ul>
          {snapshot.omittedItems.length ? (
            <div className="mt-3 rounded-lg border border-subtle bg-canvas px-3 py-2">
              <p className="text-xs font-medium text-tertiary">
                Excluded this turn
              </p>
              <ul className="mt-1 space-y-0.5">
                {snapshot.omittedItems.map((item) => (
                  <li key={item} className="text-xs text-tertiary">
                    · {item}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Section>

        {/* File excerpts */}
        <Section icon={FileText} title="File Excerpts">
          <p className="text-sm text-tertiary">
            No files attached to this turn. Upload project files to ground
            responses in real specifications.
          </p>
        </Section>
      </div>
    </div>
  );
}
