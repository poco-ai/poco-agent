"use client";

import * as React from "react";
import { Suspense } from "react";
import { useSearchParams, usePathname, useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { CapabilitiesLayoutProvider } from "@/features/capabilities/components/capabilities-layout-context";
import { Button } from "@/components/ui/button";
import type { CapabilitiesLayoutContextValue } from "@/features/capabilities/components/capabilities-layout-context";
import { CapabilitiesSidebar } from "@/features/capabilities/components/capabilities-sidebar";
import { CapabilitiesLibraryHeader } from "@/features/capabilities/components/capabilities-library-header";
import { useCapabilityViews } from "@/features/capabilities/hooks/use-capability-views";
import {
  consumePendingCapabilityView,
  setLastCapabilityView,
} from "@/features/capabilities/lib/capability-view-state";
import { useT } from "@/lib/i18n/client";

// TODO: Refactor this route-state flow and remove obsolete branches.
// Verify mobile back behavior for both home entry and sidebar entry.
// Query param semantics: `view=list` means capability list (mobile),
// while `view=<id>` means a specific capability detail view.

export function CapabilitiesPageClient() {
  const { t } = useT("translation");
  const views = useCapabilityViews();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const viewFromUrl = searchParams.get("view");
  const fromHome = searchParams.get("from") === "home";
  const [activeViewId, setActiveViewId] = React.useState<string>("skills");
  const [isDesktop, setIsDesktop] = React.useState(false);
  const [isMobileDetailVisible, setIsMobileDetailVisible] =
    React.useState(false);
  const [enteredDetailViaView, setEnteredDetailViaView] = React.useState(false);

  React.useEffect(() => {
    if (!views.length) return;

    const isMobile =
      typeof window !== "undefined" &&
      !window.matchMedia("(min-width: 768px)").matches;

    if (viewFromUrl === "list") {
      setActiveViewId("list");
      setEnteredDetailViaView(false);
      if (isMobile) setIsMobileDetailVisible(false);
      return;
    }

    if (viewFromUrl && views.some((view) => view.id === viewFromUrl)) {
      setActiveViewId(viewFromUrl);
      if (isMobile) {
        setIsMobileDetailVisible(true);
        setEnteredDetailViaView(fromHome); // back goes to home only when ?from=home
      }
      return;
    }

    const pendingViewId = consumePendingCapabilityView();
    if (pendingViewId && views.some((view) => view.id === pendingViewId)) {
      setActiveViewId(pendingViewId);
      if (isMobile) {
        setIsMobileDetailVisible(true);
        setEnteredDetailViaView(false); // pending used by other entry points (e.g. repo-dialog), not home
      }
      return;
    }

    // No view in URL and no pending: from sidebar → go to options list (?view=list)
    setActiveViewId("list");
    setEnteredDetailViaView(false);
    if (isMobile) setIsMobileDetailVisible(false);
  }, [views, viewFromUrl, fromHome]);

  React.useEffect(() => {
    if (!activeViewId || activeViewId === "list") return;
    setLastCapabilityView(activeViewId);
  }, [activeViewId]);

  // Only sync URL when there was no valid view in URL (we used pending/last/default).
  // Strip from=home on internal nav so back-from-list stays correct.
  React.useEffect(() => {
    if (!activeViewId || !views.length) return;
    const urlHasValidView =
      viewFromUrl === "list" ||
      (viewFromUrl && views.some((v) => v.id === viewFromUrl));
    if (urlHasValidView) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", activeViewId);
    params.delete("from");
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [activeViewId, pathname, router, searchParams, viewFromUrl, views]);

  React.useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const mediaQuery = window.matchMedia("(min-width: 768px)");

    const updateMatches = (matches: boolean) => {
      setIsDesktop(matches);
      if (matches) {
        setIsMobileDetailVisible(false);
      }
    };

    updateMatches(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      updateMatches(event.matches);
    };

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  const isListView = activeViewId === "list";
  const activeView = React.useMemo(() => {
    if (activeViewId === "list") return undefined;
    return views.find((view) => view.id === activeViewId) ?? views[0];
  }, [views, activeViewId]);

  const ActiveComponent = activeView?.component;
  const activeViewKey = activeView?.id ?? "unknown";

  const handleSelectView = React.useCallback(
    (viewId: string) => {
      setActiveViewId(viewId);
      const params = new URLSearchParams(searchParams.toString());
      params.set("view", viewId);
      params.delete("from");
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      if (!isDesktop) {
        setIsMobileDetailVisible(true);
      }
    },
    [isDesktop, pathname, router, searchParams],
  );

  const renderActiveView = (
    keySuffix: string,
    layoutValue: CapabilitiesLayoutContextValue,
  ) => {
    if (!ActiveComponent) return null;
    return (
      <CapabilitiesLayoutProvider value={layoutValue}>
        <Suspense fallback={<div className="h-full w-full" />}>
          <div className="flex h-full min-h-0 flex-col">
            <ActiveComponent key={`${activeViewKey}-${keySuffix}`} />
          </div>
        </Suspense>
      </CapabilitiesLayoutProvider>
    );
  };

  const showMobileBack = !isDesktop && isMobileDetailVisible;
  const headerTitle = showMobileBack
    ? (activeView?.label ?? t("library.title"))
    : t("library.title");
  const headerSubtitle = showMobileBack
    ? (activeView?.description ?? undefined)
    : isListView
      ? undefined
      : t("library.subtitle");
  const backLabel = t("library.mobile.back");
  const handleMobileBack = React.useCallback(() => {
    if (enteredDetailViaView) {
      // Came from home (card click): back goes to home
      router.back();
    } else {
      // Default: back goes to options list (?view=list)
      setIsMobileDetailVisible(false);
      setEnteredDetailViaView(false);
      const params = new URLSearchParams(searchParams.toString());
      params.set("view", "list");
      params.delete("from");
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      setActiveViewId("list");
    }
  }, [pathname, router, searchParams, enteredDetailViaView]);
  const mobileBackButton = showMobileBack ? (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="text-muted-foreground"
      aria-label={backLabel}
      title={backLabel}
      onClick={handleMobileBack}
    >
      <ChevronLeft className="size-4" />
    </Button>
  ) : null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <CapabilitiesLibraryHeader
        mobileLeading={mobileBackButton ?? undefined}
        hideSidebarTrigger={showMobileBack}
        title={headerTitle}
        subtitle={headerSubtitle}
      />
      <div className="hidden min-h-0 flex-1 md:grid md:grid-cols-[240px_minmax(0,1fr)]">
        <CapabilitiesSidebar
          views={views}
          activeViewId={isListView ? undefined : activeView?.id}
          onSelect={handleSelectView}
        />

        <main
          className="min-h-0 overflow-hidden"
          data-onboarding="capabilities-detail"
        >
          {isDesktop && !isListView
            ? renderActiveView("desktop", { isMobileDetail: false })
            : null}
        </main>
      </div>

      <div className="flex min-h-0 flex-1 md:hidden">
        {isMobileDetailVisible ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div
              className="min-h-0 flex-1 overflow-y-auto"
              data-onboarding="capabilities-detail"
            >
              {renderActiveView("mobile", {
                isMobileDetail: true,
                onMobileBack: handleMobileBack,
                mobileBackLabel: t("library.mobile.back"),
              })}
            </div>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <CapabilitiesSidebar
              views={views}
              activeViewId={isListView ? undefined : activeView?.id}
              onSelect={handleSelectView}
              variant="mobile"
            />
          </div>
        )}
      </div>
    </div>
  );
}
