"use client";

import { useEffect, useState } from "react";
import { absoluteTime, relativeTime } from "@/lib/format";

/** Renders a relative timestamp, computed on the client after mount to avoid
 * hydration mismatches. Shows an absolute time on hover. */
export function TimeAgo({ iso, className }: { iso: string; className?: string }) {
  const [label, setLabel] = useState("");

  useEffect(() => {
    const update = () => setLabel(relativeTime(iso));
    update();
    const t = setInterval(update, 60_000);
    return () => clearInterval(t);
  }, [iso]);

  return (
    <time
      dateTime={iso}
      title={absoluteTime(iso)}
      className={className}
      suppressHydrationWarning
    >
      {label}
    </time>
  );
}
