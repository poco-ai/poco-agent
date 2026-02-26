import { useCallback } from "react";
import { useSidebar } from "@/components/ui/sidebar";

/**
 * Hook to manage mobile sidebar close behavior.
 *
 * Provides a convenient way to close the mobile sidebar after navigation
 * or user actions.
 */
export function useMobileSidebar() {
  const { isMobile, setOpenMobile } = useSidebar();

  const closeMobileSidebar = useCallback(() => {
    if (isMobile) setOpenMobile(false);
  }, [isMobile, setOpenMobile]);

  return { closeMobileSidebar, isMobile };
}
