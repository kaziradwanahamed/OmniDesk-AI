import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

/** Returns false during SSR and the first client render, true afterwards —
 * without a setState-in-effect, so it is safe for client-only rendering. */
export function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}
