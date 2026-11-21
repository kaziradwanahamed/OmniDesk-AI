"use client";

import * as React from "react";
import { FileText, Layers, ListChecks, NotebookPen, Pin } from "lucide-react";
import type { Project, ProjectInstructions } from "@/lib/types";

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-subtle px-4 py-4">
      <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold tracking-wide text-tertiary uppercase">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </h3>
      {children}
    </section>
  );
}

export function LiveContextPanel({
  project,
  instructions,
}: {
  project: Project | null;
  instructions: ProjectInstructions | null;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-subtle px-4 py-3.5">
        <h2 className="text-sm font-semibold text-primary">Context Included</h2>
        <p className="mt-0.5 text-xs text-secondary">
          The project context sent to the model on each turn.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <Section icon={NotebookPen} title="Project">
          {project ? (
            <>
              <p className="text-sm font-medium text-primary">{project.name}</p>
              {project.description ? (
                <p className="mt-1 text-sm text-secondary">{project.description}</p>
              ) : null}
              {project.goals ? (
                <p className="mt-2 text-xs text-tertiary">
                  <span className="font-medium">Goals:</span> {project.goals}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-tertiary">—</p>
          )}
        </Section>

        <Section
          icon={Pin}
          title={
            instructions ? `Instructions (v${instructions.version})` : "Instructions"
          }
        >
          {instructions ? (
            <>
              <p className="text-sm leading-relaxed text-secondary">
                {instructions.content}
              </p>
              {instructions.responseStyle ? (
                <p className="mt-2 text-xs text-tertiary">
                  <span className="font-medium">Style:</span>{" "}
                  {instructions.responseStyle}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-tertiary">
              No instructions set yet. Add them in Project settings.
            </p>
          )}
        </Section>

        <Section icon={Layers} title="Upcoming context">
          <ul className="space-y-1.5 text-xs text-tertiary">
            <li className="flex items-center gap-1.5">
              <ListChecks className="h-3.5 w-3.5" />
              Decisions &amp; active task — Phase 6
            </li>
            <li className="flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5" />
              Rolling summary &amp; token budget — Phase 7
            </li>
            <li className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              File excerpts — Phase 9
            </li>
          </ul>
        </Section>
      </div>
    </div>
  );
}
