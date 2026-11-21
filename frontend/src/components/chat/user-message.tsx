import { TimeAgo } from "@/components/shared/time-ago";
import type { ChatMessage } from "@/lib/types";

export function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex w-full justify-end py-3">
      <div className="max-w-[85%] rounded-2xl rounded-br-md border border-subtle bg-elevated px-4 py-2.5">
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-primary">
          {message.content}
        </p>
        <div className="mt-1 text-right">
          <TimeAgo
            iso={message.createdAt}
            className="font-mono text-[10px] text-tertiary"
          />
        </div>
      </div>
    </div>
  );
}
