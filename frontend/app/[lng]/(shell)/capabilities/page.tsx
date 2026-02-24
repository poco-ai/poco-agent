import { Suspense } from "react";
import { CapabilitiesPageClient } from "@/features/capabilities";

export default function CapabilitiesPage() {
  return (
    <Suspense fallback={null}>
      <CapabilitiesPageClient />
    </Suspense>
  );
}
