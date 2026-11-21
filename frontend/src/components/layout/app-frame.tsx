"use client";

import { useState, useSyncExternalStore } from "react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Sidebar } from "./sidebar";
import { SidebarContext } from "./sidebar-context";
import { sidebarStore } from "@/lib/sidebar-store";
import { cn } from "@/lib/cn";

export function AppFrame({ children }: { children: React.ReactNode }) {
  const collapsed = useSyncExternalStore(
    sidebarStore.subscribe,
    sidebarStore.getSnapshot,
    sidebarStore.getServerSnapshot,
  );
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <SidebarContext.Provider
      value={{
        openMobile: () => setMobileOpen(true),
        closeMobile: () => setMobileOpen(false),
        collapsed,
        toggleCollapsed: sidebarStore.toggle,
      }}
    >
      <div className="flex h-dvh overflow-hidden">
        <aside
          className={cn(
            "hidden shrink-0 overflow-hidden border-r border-subtle bg-surface transition-[width] duration-200 lg:block",
            collapsed ? "w-0 border-r-0" : "w-[260px]",
          )}
        >
          {!collapsed ? <Sidebar /> : null}
        </aside>

        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left" className="w-[280px]">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </SheetContent>
        </Sheet>

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {children}
        </div>
      </div>
    </SidebarContext.Provider>
  );
}
