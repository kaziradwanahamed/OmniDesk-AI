"use client";

import { createContext, useContext } from "react";

interface SidebarCtx {
  openMobile: () => void;
  closeMobile: () => void;
  collapsed: boolean;
  toggleCollapsed: () => void;
}

export const SidebarContext = createContext<SidebarCtx | null>(null);

const NOOP: SidebarCtx = {
  openMobile: () => {},
  closeMobile: () => {},
  collapsed: false,
  toggleCollapsed: () => {},
};

export function useSidebar(): SidebarCtx {
  return useContext(SidebarContext) ?? NOOP;
}
