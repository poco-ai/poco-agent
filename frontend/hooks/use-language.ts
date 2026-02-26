import { useParams } from "next/navigation";
import { useMemo } from "react";

/**
 * Hook to extract the language parameter from the current route.
 *
 * Handles both single and array parameter values from Next.js dynamic routes.
 * Returns undefined if no language parameter is present.
 */
export function useLanguage() {
  const params = useParams();
  return useMemo(() => {
    const value = params?.lng;
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);
}
