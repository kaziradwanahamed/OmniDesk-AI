/** Tiny external store for the persisted sidebar-collapsed preference, read via
 * useSyncExternalStore so it is SSR-safe and avoids setState-in-effect. */

const KEY = "omni:sidebar-collapsed";
const listeners = new Set<() => void>();

function read(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export const sidebarStore = {
  subscribe(cb: () => void) {
    listeners.add(cb);
    return () => {
      listeners.delete(cb);
    };
  },
  getSnapshot: read,
  getServerSnapshot: () => false,
  toggle() {
    const next = !read();
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch {
      /* storage unavailable */
    }
    listeners.forEach((l) => l());
  },
};
