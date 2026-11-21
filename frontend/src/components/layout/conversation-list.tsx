"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Loader2, MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConversations } from "@/components/conversations/conversations-provider";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import type { Conversation } from "@/lib/types";

export function ConversationList({
  projectId,
  onNavigate,
}: {
  projectId: string;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const {
    conversations,
    loading,
    addConversation,
    updateConversationLocal,
    removeConversation,
  } = useConversations();

  const [creating, setCreating] = useState(false);
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null);
  const [busy, setBusy] = useState(false);

  async function newConversation() {
    setCreating(true);
    try {
      const c = await api.createConversation(projectId, "New conversation");
      addConversation(c);
      onNavigate?.();
      router.push(`/projects/${projectId}/chat/${c.id}`);
    } catch {
      /* ignore */
    } finally {
      setCreating(false);
    }
  }

  async function doRename() {
    if (!renameTarget || !renameValue.trim()) return;
    setBusy(true);
    try {
      const c = await api.renameConversation(renameTarget.id, renameValue.trim());
      updateConversationLocal(c);
      setRenameTarget(null);
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  async function doDelete() {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setBusy(true);
    try {
      await api.deleteConversation(id);
      removeConversation(id);
      setDeleteTarget(null);
      if (pathname.includes(`/chat/${id}`)) {
        router.push(`/projects/${projectId}/chat`);
      }
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col px-2">
      <div className="mb-1 flex items-center justify-between px-1">
        <span className="text-xs font-semibold tracking-wide text-tertiary uppercase">
          Conversations
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="New conversation"
          onClick={newConversation}
          disabled={creating}
        >
          {creating ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-1 pb-2">
        {loading ? (
          <p className="px-2.5 py-3 text-xs text-tertiary">Loading…</p>
        ) : conversations.length ? (
          conversations.map((c) => {
            const active = pathname === `/projects/${projectId}/chat/${c.id}`;
            return (
              <div
                key={c.id}
                className={cn(
                  "group/conv flex items-center gap-1 rounded-md pr-1 transition-colors",
                  active ? "bg-elevated" : "hover:bg-surface",
                )}
              >
                <Link
                  href={`/projects/${projectId}/chat/${c.id}`}
                  onClick={onNavigate}
                  className="min-w-0 flex-1 px-2.5 py-2"
                >
                  <span
                    className={cn(
                      "block truncate text-sm",
                      active ? "font-medium text-primary" : "text-secondary",
                    )}
                  >
                    {c.title}
                  </span>
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Conversation actions"
                      className="opacity-0 group-hover/conv:opacity-100 data-[state=open]:opacity-100"
                    >
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onSelect={() => {
                        setRenameTarget(c);
                        setRenameValue(c.title);
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="text-danger focus:bg-danger/10"
                      onSelect={() => setDeleteTarget(c)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            );
          })
        ) : (
          <p className="px-2.5 py-3 text-xs text-tertiary">
            No conversations yet. Create one to start chatting.
          </p>
        )}
      </div>

      <Dialog
        open={renameTarget !== null}
        onOpenChange={(o) => !o && setRenameTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename conversation</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void doRename();
            }}
            className="space-y-3"
          >
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setRenameTarget(null)}
                disabled={busy}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={busy || !renameValue.trim()}>
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete conversation?</DialogTitle>
            <DialogDescription>
              This permanently deletes{" "}
              <span className="font-medium text-primary">
                {deleteTarget?.title}
              </span>{" "}
              and its messages.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => setDeleteTarget(null)}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button variant="danger" onClick={doDelete} disabled={busy}>
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
