import { Suspense } from "react";
import { CapabilitiesPageClient } from "@/features/capabilities/components/capabilities-page-client";

export default function CapabilitiesPage() {
  return (
    <Suspense fallback={null}>
      <CapabilitiesPageClient />
    </Suspense>
  );
}
