"use client";

import { useParams } from "next/navigation";
import { FileText, Upload } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { sampleProjects } from "@/lib/sample";

export default function FilesPage() {
  const params = useParams<{ projectId: string }>();
  const project =
    sampleProjects.find((p) => p.id === params.projectId) ?? sampleProjects[0];

  return (
    <>
      <PageHeader
        title="Files"
        description={project.name}
        actions={
          <Button size="sm">
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <EmptyState
            icon={FileText}
            title="No files yet"
            description="Upload specs, source files, or docs to ground responses in real content. Allowed: .md .txt .py .ts .tsx .json .yaml .sql .csv .pdf — up to 10 MB each."
            action={
              <Button variant="secondary">
                <Upload className="h-4 w-4" />
                Upload files
              </Button>
            }
          />
        </div>
      </div>
    </>
  );
}
