"use client";

import { CapabilitiesHeader } from "@/features/capabilities/components/capabilities-header";
import { CapabilitiesGrid } from "@/features/capabilities/components/capabilities-grid";

export function CapabilitiesPageClient() {
  return (
    <>
      <CapabilitiesHeader />

      <div className="flex-1 overflow-y-scroll scrollbar-hide px-6 py-10">
        <div className="w-full max-w-6xl mx-auto">
          <CapabilitiesGrid />
        </div>
      </div>
    </>
  );
}
