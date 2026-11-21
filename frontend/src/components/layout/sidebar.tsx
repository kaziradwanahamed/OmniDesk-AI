"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  ChevronsUpDown,
  FileText,
  LayoutGrid,
  Layers,
  LogOut,
  MessageSquare,
  NotebookPen,
  PanelLeftClose,
  Plus,
  Settings2,
  SlidersHorizontal,
  User,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { useAuth } from "@/components/auth/auth-provider";
import { useProjects } from "@/components/projects/projects-provider";
import { useSidebar } from "./sidebar-context";
import { ConversationList } from "./conversation-list";
import { cn } from "@/lib/cn";

function NavLink({
  href,
  base,
  label,
  icon: Icon,
  pathname,
  onNavigate,
}: {
  href: string;
  base: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  pathname: string;
  onNavigate?: () => void;
}) {
  const active =
    pathname === base || pathname.startsWith(base + "/") || pathname === href;
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
        active
          ? "bg-elevated font-medium text-primary"
          : "text-secondary hover:bg-surface hover:text-primary",
      )}
    >
      <Icon className={cn("h-4 w-4", active ? "text-accent" : "text-tertiary")} />
      <span className="truncate">{label}</span>
    </Link>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { toggleCollapsed } = useSidebar();
  const { user, logout } = useAuth();
  const { projects, loading } = useProjects();

  const routeMatch = pathname.match(/^\/projects\/([^/]+)/);
  const currentProjectId = routeMatch?.[1] ?? projects[0]?.id ?? null;
  const currentProject = projects.find((p) => p.id === currentProjectId) ?? null;

  const projectNav = currentProjectId
    ? [
        {
          label: "Chat",
          icon: MessageSquare,
          href: `/projects/${currentProjectId}/chat`,
          base: `/projects/${currentProjectId}/chat`,
        },
        {
          label: "Memory & Instructions",
          icon: NotebookPen,
          href: `/projects/${currentProjectId}/context`,
          base: `/projects/${currentProjectId}/context`,
        },
        {
          label: "Files",
          icon: FileText,
          href: `/projects/${currentProjectId}/files`,
          base: `/projects/${currentProjectId}/files`,
        },
        {
          label: "Settings",
          icon: Settings2,
          href: `/projects/${currentProjectId}/settings`,
          base: `/projects/${currentProjectId}/settings`,
        },
      ]
    : [];

  const globalNav = [
    { label: "Usage", icon: BarChart3, href: "/usage", base: "/usage" },
    {
      label: "Provider Settings",
      icon: SlidersHorizontal,
      href: "/settings/providers",
      base: "/settings/providers",
    },
  ];

  const accountLabel = user.displayName || user.email;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-14 shrink-0 items-center gap-2 px-3">
        <Link
          href="/projects"
          onClick={onNavigate}
          className="flex min-w-0 items-center gap-2"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-fg">
            <Layers className="h-4 w-4" />
          </span>
          <span className="truncate text-sm font-semibold text-primary">
            OmniDesk AI
          </span>
        </Link>
        <Button
          variant="ghost"
          size="icon-sm"
          className="ml-auto hidden lg:inline-flex"
          onClick={toggleCollapsed}
          aria-label="Collapse sidebar"
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      {/* Project switcher */}
      <div className="flex items-center gap-1.5 px-3 pb-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-subtle bg-canvas px-2.5 py-1.5 text-sm outline-none transition-colors hover:border-strong focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              <span className="truncate font-medium text-primary">
                {loading
                  ? "Loading…"
                  : currentProject?.name ?? "No project selected"}
              </span>
              <ChevronsUpDown className="ml-auto h-3.5 w-3.5 shrink-0 text-tertiary" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="max-h-80 w-[13rem] overflow-y-auto">
            <DropdownMenuLabel>Projects</DropdownMenuLabel>
            {projects.length ? (
              projects.map((p) => (
                <DropdownMenuItem key={p.id} asChild>
                  <Link href={`/projects/${p.id}/settings`} onClick={onNavigate}>
                    {p.name}
                  </Link>
                </DropdownMenuItem>
              ))
            ) : (
              <div className="px-2 py-2 text-xs text-tertiary">No projects yet.</div>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/projects" onClick={onNavigate}>
                <Plus className="h-3.5 w-3.5" />
                New project
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Nav */}
      <nav className="space-y-0.5 px-2">
        <NavLink
          href="/projects"
          base="/projects"
          label="All projects"
          icon={LayoutGrid}
          pathname={pathname}
          onNavigate={onNavigate}
        />
      </nav>

      {projectNav.length ? (
        <div className="mt-3 px-2">
          <p className="mb-1 px-2.5 text-xs font-semibold tracking-wide text-tertiary uppercase">
            {currentProject?.name ?? "Project"}
          </p>
          <nav className="space-y-0.5">
            {projectNav.map((item) => (
              <NavLink
                key={item.label}
                {...item}
                pathname={pathname}
                onNavigate={onNavigate}
              />
            ))}
          </nav>
        </div>
      ) : null}

      <div className="mt-3 px-2">
        <nav className="space-y-0.5">
          {globalNav.map((item) => (
            <NavLink
              key={item.label}
              {...item}
              pathname={pathname}
              onNavigate={onNavigate}
            />
          ))}
        </nav>
      </div>

      {/* Conversations */}
      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        {currentProjectId ? (
          <ConversationList
            projectId={currentProjectId}
            onNavigate={onNavigate}
          />
        ) : (
          <p className="px-4 text-xs text-tertiary">
            Select a project to see its conversations.
          </p>
        )}
      </div>

      {/* Footer: account + theme */}
      <div className="flex items-center gap-2 border-t border-subtle px-3 py-2.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 py-1 text-left outline-none transition-colors hover:bg-surface focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-subtle bg-elevated text-tertiary">
                <User className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-primary">
                  {accountLabel}
                </span>
                <span className="block truncate text-[11px] text-tertiary">
                  {user.email}
                </span>
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-[13rem]">
            <DropdownMenuLabel>Account</DropdownMenuLabel>
            <DropdownMenuItem asChild>
              <Link href="/settings/providers" onClick={onNavigate}>
                <SlidersHorizontal className="h-3.5 w-3.5" />
                Provider settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void logout()}>
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ThemeToggle />
      </div>
    </div>
  );
}
