import { AssistantMessage } from "./assistant-message";
import { ModelSwitchDivider } from "./model-switch-divider";
import { StreamingIndicator } from "./streaming-indicator";
import { UserMessage } from "./user-message";
import type { ChatMessage } from "@/lib/types";

export function MessageTimeline({
  messages,
  streaming,
}: {
  messages: ChatMessage[];
  streaming?: boolean;
}) {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      {messages.map((m) => {
        if (m.role === "system_event") {
          return <ModelSwitchDivider key={m.id} message={m} />;
        }
        if (m.role === "user") {
          return <UserMessage key={m.id} message={m} />;
        }
        return <AssistantMessage key={m.id} message={m} />;
      })}
      {streaming ? <StreamingIndicator /> : null}
    </div>
  );
}
