"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { Project } from "@/lib/types";

interface ProjectsCtx {
  projects: Project[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  addProject: (project: Project) => void;
  updateProjectLocal: (project: Project) => void;
  removeProject: (id: string) => void;
}

const Ctx = createContext<ProjectsCtx | null>(null);

export function useProjects(): ProjectsCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProjects must be used within ProjectsProvider");
  return ctx;
}

export function ProjectsProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setProjects(await api.listProjects());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list = await api.listProjects();
        if (active) setProjects(list);
      } catch (e) {
        if (active)
          setError(e instanceof Error ? e.message : "Failed to load projects");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const addProject = (project: Project) =>
    setProjects((prev) => [project, ...prev]);
  const updateProjectLocal = (project: Project) =>
    setProjects((prev) => prev.map((p) => (p.id === project.id ? project : p)));
  const removeProject = (id: string) =>
    setProjects((prev) => prev.filter((p) => p.id !== id));

  return (
    <Ctx.Provider
      value={{
        projects,
        loading,
        error,
        refresh,
        addProject,
        updateProjectLocal,
        removeProject,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
