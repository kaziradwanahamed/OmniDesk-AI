import { AssistantMessage } from "./assistant-message";
import { ModelSwitchDivider } from "./model-switch-divider";
import { MultiModelGrid, type MultiModelError } from "./multi-model-grid";
import { StreamingIndicator } from "./streaming-indicator";
import { UserMessage } from "./user-message";
import type { ModelOption, ModelSelection } from "./chat-composer";
import type { ChatMessage, MessageGroupInfo } from "@/lib/types";

export function MessageTimeline({
  messages,
  streaming,
  groups,
  groupErrors,
  targets,
  busyGroupId,
  onSelect,
  onCritique,
  onSynthesize,
}: {
  messages: ChatMessage[];
  streaming?: boolean;
  groups?: Record<string, MessageGroupInfo>;
  groupErrors?: Record<string, MultiModelError[]>;
  targets?: ModelOption[];
  busyGroupId?: string | null;
  onSelect?: (groupId: string, messageId: string) => void;
  onCritique?: (groupId: string, subjectId: string, target: ModelSelection) => void;
  onSynthesize?: (groupId: string, sourceIds: string[], target: ModelSelection) => void;
}) {
  const seen = new Set<string>();
  return (
    <div className="mx-auto w-full max-w-5xl px-4 pb-4">
      {messages.map((m) => {
        if (m.role === "system_event") {
          return (
            <div key={m.id} className="mx-auto w-full max-w-3xl">
              <ModelSwitchDivider message={m} />
            </div>
          );
        }
        if (m.role === "user") {
          return (
            <div key={m.id} className="mx-auto w-full max-w-3xl">
              <UserMessage message={m} />
            </div>
          );
        }
        // assistant — render a group once as a grid, singletons as a bubble.
        if (m.groupId) {
          if (seen.has(m.groupId)) return null;
          const groupId = m.groupId;
          seen.add(groupId);
          const groupMsgs = messages.filter((x) => x.groupId === groupId);
          const info = groups?.[groupId] ?? null;
          return (
            <MultiModelGrid
              key={groupId}
              responses={groupMsgs}
              errors={groupErrors?.[groupId] ?? []}
              selectedMessageId={info?.selectedMessageId ?? null}
              targets={targets ?? []}
              busy={busyGroupId === groupId}
              onSelect={(mid) => onSelect?.(groupId, mid)}
              onCritique={(sid, t) => onCritique?.(groupId, sid, t)}
              onSynthesize={(sids, t) => onSynthesize?.(groupId, sids, t)}
            />
          );
        }
        return (
          <div key={m.id} className="mx-auto w-full max-w-3xl">
            <AssistantMessage message={m} />
          </div>
        );
      })}
      {streaming ? (
        <div className="mx-auto w-full max-w-3xl">
          <StreamingIndicator />
        </div>
      ) : null}
    </div>
  );
}
