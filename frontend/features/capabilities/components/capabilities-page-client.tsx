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
  getLastCapabilityView,
  setLastCapabilityView,
} from "@/features/capabilities/lib/capability-view-state";
import { useT } from "@/lib/i18n/client";

export function CapabilitiesPageClient() {
  const { t } = useT("translation");
  const views = useCapabilityViews();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const viewFromUrl = searchParams.get("view");
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

    if (viewFromUrl && views.some((view) => view.id === viewFromUrl)) {
      setActiveViewId(viewFromUrl);
      if (isMobile) {
        setIsMobileDetailVisible(true);
        setEnteredDetailViaView(true);
      }
      return;
    }

    const pendingViewId = consumePendingCapabilityView();
    if (pendingViewId && views.some((view) => view.id === pendingViewId)) {
      setActiveViewId(pendingViewId);
      if (isMobile) {
        setIsMobileDetailVisible(true);
        setEnteredDetailViaView(true);
      }
      return;
    }

    const lastViewId = getLastCapabilityView();
    if (lastViewId && views.some((view) => view.id === lastViewId)) {
      setActiveViewId(lastViewId);
      return;
    }

    const defaultViewId =
      views.find((view) => view.id === "skills")?.id ??
      views[0]?.id ??
      "skills";
    setActiveViewId(defaultViewId);
  }, [views, viewFromUrl]);

  React.useEffect(() => {
    if (!activeViewId) return;
    setLastCapabilityView(activeViewId);
  }, [activeViewId]);

  // Only sync URL when there was no valid view in URL (we used pending/last/default).
  // Do not overwrite an existing ?view= — that causes flicker (URL gets overwritten before state updates).
  React.useEffect(() => {
    if (!activeViewId || !views.length) return;
    const urlHasValidView =
      viewFromUrl && views.some((v) => v.id === viewFromUrl);
    if (urlHasValidView) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", activeViewId);
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

  const activeView = React.useMemo(() => {
    return views.find((view) => view.id === activeViewId) ?? views[0];
  }, [views, activeViewId]);

  const ActiveComponent = activeView?.component;
  const activeViewKey = activeView?.id ?? "unknown";

  const handleSelectView = React.useCallback(
    (viewId: string) => {
      setActiveViewId(viewId);
      const params = new URLSearchParams(searchParams.toString());
      params.set("view", viewId);
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
    : t("library.subtitle");
  const backLabel = t("library.mobile.back");
  const handleMobileBack = React.useCallback(() => {
    if (enteredDetailViaView) {
      router.back();
    } else {
      setIsMobileDetailVisible(false);
    }
  }, [router, enteredDetailViaView]);
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
          activeViewId={activeView?.id}
          onSelect={handleSelectView}
        />

        <main className="min-h-0 overflow-hidden">
          {isDesktop
            ? renderActiveView("desktop", { isMobileDetail: false })
            : null}
        </main>
      </div>

      <div className="flex min-h-0 flex-1 md:hidden">
        {isMobileDetailVisible ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="min-h-0 flex-1 overflow-y-auto">
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
              activeViewId={activeView?.id}
              onSelect={handleSelectView}
              variant="mobile"
            />
          </div>
        )}
      </div>
    </div>
  );
}
