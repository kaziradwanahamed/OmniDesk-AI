"use client";

import { Menu, PanelLeftOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSidebar } from "./sidebar-context";

/** Left-edge control in page headers: opens the mobile drawer, or expands the
 * collapsed desktop sidebar. */
export function SidebarToggle() {
  const { openMobile, collapsed, toggleCollapsed } = useSidebar();
  return (
    <>
      <Button
        variant="ghost"
        size="icon-sm"
        className="lg:hidden"
        onClick={openMobile}
        aria-label="Open navigation"
      >
        <Menu className="h-4 w-4" />
      </Button>
      {collapsed ? (
        <Button
          variant="ghost"
          size="icon-sm"
          className="hidden lg:inline-flex"
          onClick={toggleCollapsed}
          aria-label="Expand sidebar"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </Button>
      ) : null}
    </>
  );
}
