"use client";

import * as React from "react";
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  Languages,
  LogOut,
  Palette,
  Server,
  SlidersHorizontal,
  User,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { useIsMobile } from "@/hooks/use-mobile";
import { useThemeMode } from "@/hooks/use-theme-mode";
import { SettingsSidebar } from "@/features/settings/components/settings-sidebar";
import { AccountSettingsTab } from "@/features/settings/components/tabs/account-settings-tab";
import { ModelsSettingsTab } from "@/features/settings/components/tabs/models-settings-tab";
import { UsageSettingsTab } from "@/features/settings/components/tabs/usage-settings-tab";
import {
  useBackendPreference,
  type BackendOption,
} from "@/features/settings/hooks/use-backend-preference";
import { useSettingsLanguage } from "@/features/settings/hooks/use-settings-language";
import type {
  ApiProviderConfig,
  SettingsSidebarItem,
  SettingsTabId,
  SettingsTabRequest,
} from "@/features/settings/types";
import { useUserAccount } from "@/features/user/hooks/use-user-account";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tabRequest?: SettingsTabRequest | null;
}

type MobileView = "overview" | SettingsTabId;

type SettingOption = {
  value: string;
  label: string;
  description?: string;
};

const MOBILE_SHEET_CLOSE_THRESHOLD = 140;

const DEFAULT_OPENAI_CONFIG: ApiProviderConfig = {
  enabled: false,
  key: "",
  useCustomBaseUrl: false,
  baseUrl: "https://api.openai.com/v1",
};

const DEFAULT_ANTHROPIC_CONFIG: ApiProviderConfig = {
  enabled: false,
  key: "",
  useCustomBaseUrl: false,
  baseUrl: "https://api.anthropic.com",
};

export function SettingsDialog({
  open,
  onOpenChange,
  tabRequest,
}: SettingsDialogProps) {
  const { t } = useT("translation");
  const isMobile = useIsMobile();
  const router = useRouter();
  const { mode, setMode } = useThemeMode();
  const { backend, setBackend } = useBackendPreference();
  const { currentLanguage, changeLanguage } = useSettingsLanguage();
  const { profile, credits, isLoading } = useUserAccount();

  const [activeTab, setActiveTab] = React.useState<SettingsTabId>(
    tabRequest?.tab ?? "account",
  );
  const [mobileView, setMobileView] = React.useState<MobileView>("overview");
  const [isGlmEnabled, setIsGlmEnabled] = React.useState(true);
  const [openAiConfig, setOpenAiConfig] = React.useState(DEFAULT_OPENAI_CONFIG);
  const [anthropicConfig, setAnthropicConfig] = React.useState(
    DEFAULT_ANTHROPIC_CONFIG,
  );

  const dragHandleRef = React.useRef<HTMLDivElement | null>(null);
  const dragStartYRef = React.useRef(0);
  const dragPointerIdRef = React.useRef<number | null>(null);
  const translateYRef = React.useRef(0);
  const [dragOffset, setDragOffset] = React.useState(0);
  const [isDraggingSheet, setIsDraggingSheet] = React.useState(false);

  const updateDragOffset = React.useCallback((value: number) => {
    translateYRef.current = value;
    setDragOffset(value);
  }, []);

  const resetDragState = React.useCallback(() => {
    dragPointerIdRef.current = null;
    dragStartYRef.current = 0;
    translateYRef.current = 0;
    setIsDraggingSheet(false);
    setDragOffset(0);
  }, []);

  const handleSheetOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        setMobileView("overview");
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange],
  );

  const handleClose = React.useCallback(() => {
    handleSheetOpenChange(false);
  }, [handleSheetOpenChange]);

  const shouldStartDrag = React.useCallback((target: EventTarget | null) => {
    if (!dragHandleRef.current) return false;
    if (!(target instanceof HTMLElement)) return false;
    if (target.closest("[data-prevent-drag=true]")) return false;
    return dragHandleRef.current.contains(target);
  }, []);

  const handlePointerDown = React.useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isMobile) return;
      if (event.pointerType === "mouse") return;
      if (!shouldStartDrag(event.target)) return;
      dragStartYRef.current = event.clientY;
      dragPointerIdRef.current = event.pointerId;
      updateDragOffset(0);
      setIsDraggingSheet(true);
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [isMobile, shouldStartDrag, updateDragOffset],
  );

  const handlePointerMove = React.useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isMobile) return;
      if (!isDraggingSheet) return;
      if (dragPointerIdRef.current !== event.pointerId) return;
      const offset = Math.max(event.clientY - dragStartYRef.current, 0);
      updateDragOffset(offset);
    },
    [isMobile, isDraggingSheet, updateDragOffset],
  );

  const handlePointerEnd = React.useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isMobile) return;
      if (!isDraggingSheet) return;
      if (dragPointerIdRef.current !== event.pointerId) return;
      event.currentTarget.releasePointerCapture(event.pointerId);
      const shouldClose = translateYRef.current > MOBILE_SHEET_CLOSE_THRESHOLD;
      resetDragState();
      if (shouldClose) {
        handleClose();
      }
    },
    [handleClose, isDraggingSheet, isMobile, resetDragState],
  );

  const handlePointerCancel = React.useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isMobile) return;
      if (dragPointerIdRef.current !== event.pointerId) return;
      event.currentTarget.releasePointerCapture(event.pointerId);
      resetDragState();
    },
    [isMobile, resetDragState],
  );

  const sidebarItems = React.useMemo<SettingsSidebarItem[]>(
    () => [
      { icon: User, label: t("settings.sidebar.account"), id: "account" },
      { icon: Server, label: t("settings.sidebar.models"), id: "models" },
      { icon: Activity, label: t("settings.sidebar.usage"), id: "usage" },
    ],
    [t],
  );

  const activeTitle = React.useMemo(
    () => sidebarItems.find((item) => item.id === activeTab)?.label,
    [activeTab, sidebarItems],
  );

  const languageOptions = React.useMemo<SettingOption[]>(
    () => [
      { value: "en", label: t("settings.english") },
      { value: "zh", label: t("settings.simplifiedChinese") },
      { value: "fr", label: t("settings.french") },
      { value: "ja", label: t("settings.japanese") },
      { value: "de", label: t("settings.german") },
      { value: "ru", label: t("settings.russian") },
    ],
    [t],
  );

  const backendOptions = React.useMemo<SettingOption[]>(
    () => [{ value: "claude-code", label: t("settings.claudeCode") }],
    [t],
  );

  const themeOptions = React.useMemo<SettingOption[]>(
    () => [
      { value: "light", label: t("settings.lightMode") },
      { value: "dark", label: t("settings.darkMode") },
    ],
    [t],
  );

  const mobileHeaderTitle = React.useMemo(() => {
    if (mobileView === "overview") return t("settings.dialogTitle");
    return (
      sidebarItems.find((item) => item.id === mobileView)?.label ??
      t("settings.dialogTitle")
    );
  }, [mobileView, sidebarItems, t]);

  const sheetMotionStyle = React.useMemo<React.CSSProperties | undefined>(
    () =>
      isMobile
        ? {
            transform:
              dragOffset > 0 ? `translate3d(0, ${dragOffset}px, 0)` : undefined,
            transition: isDraggingSheet ? "none" : "transform 0.25s ease",
          }
        : undefined,
    [dragOffset, isDraggingSheet, isMobile],
  );

  React.useEffect(() => {
    if (!open) {
      setMobileView("overview");
      resetDragState();
    }
  }, [open, resetDragState]);

  React.useEffect(() => {
    if (!open) return;
    if (!tabRequest) return;
    setActiveTab(tabRequest.tab);
    if (isMobile) {
      setMobileView(tabRequest.tab);
    }
  }, [open, tabRequest, isMobile]);

  React.useEffect(() => {
    if (!open) return;
    if (tabRequest) return;
    setActiveTab("account");
    if (isMobile) {
      setMobileView("overview");
    }
  }, [open, tabRequest, isMobile]);

  const updateOpenAiConfig = React.useCallback(
    (patch: Partial<ApiProviderConfig>) => {
      setOpenAiConfig((prev) => ({ ...prev, ...patch }));
    },
    [],
  );

  const updateAnthropicConfig = React.useCallback(
    (patch: Partial<ApiProviderConfig>) => {
      setAnthropicConfig((prev) => ({ ...prev, ...patch }));
    },
    [],
  );

  const handleLogout = React.useCallback(() => {
    router.push("/login");
    handleClose();
  }, [router, handleClose]);

  const handleMobileNavigate = (view: MobileView) => {
    if (view === "overview") {
      setMobileView("overview");
      return;
    }

    if (view === "account" || view === "models" || view === "usage") {
      setActiveTab(view);
    }

    setMobileView(view);
  };

  const handleHelp = React.useCallback(() => {
    window.open(t("settings.getHelpUrl"), "_blank");
  }, [t]);

  const renderContent = () => {
    if (activeTab === "account") {
      return (
        <AccountSettingsTab
          profile={profile}
          credits={credits}
          isLoading={isLoading}
        />
      );
    }

    if (activeTab === "models") {
      return (
        <ModelsSettingsTab
          isGlmEnabled={isGlmEnabled}
          openAiConfig={openAiConfig}
          anthropicConfig={anthropicConfig}
          onToggleGlm={setIsGlmEnabled}
          onUpdateOpenAiConfig={updateOpenAiConfig}
          onUpdateAnthropicConfig={updateAnthropicConfig}
        />
      );
    }

    return <UsageSettingsTab />;
  };

  const renderMobileSecondary = () => (
    <div className="min-h-0 flex-1 overflow-hidden rounded-3xl border border-border/50 bg-card/70">
      {renderContent()}
    </div>
  );

  if (!isMobile) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent
          className="!max-w-[1000px] !h-[75vh] flex w-[90vw] min-h-[500px] max-h-[800px] flex-col gap-0 overflow-hidden bg-background p-0 text-foreground"
          showCloseButton={false}
        >
          <DialogHeader className="sr-only">
            <DialogTitle>{t("settings.dialogTitle")}</DialogTitle>
          </DialogHeader>

          <div className="flex min-h-0 flex-1">
            <SettingsSidebar
              items={sidebarItems}
              activeTab={activeTab}
              onSelectTab={setActiveTab}
            />

            <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-background">
              <div className="flex shrink-0 items-center justify-between p-5 pb-2">
                <h2 className="text-xl font-semibold">{activeTitle}</h2>
              </div>
              {renderContent()}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Sheet open={open} onOpenChange={handleSheetOpenChange}>
      <SheetContent
        side="bottom"
        className="flex h-[92vh] w-full max-h-[96vh] flex-col rounded-t-3xl border border-border/20 bg-background px-4 pb-6 pt-3 shadow-[var(--shadow-xl)] sm:px-6 [&>button:last-child]:hidden"
        style={sheetMotionStyle}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerCancel}
      >
        <SheetHeader className="sr-only">
          <SheetTitle>{t("settings.dialogTitle")}</SheetTitle>
        </SheetHeader>

        <div ref={dragHandleRef} className="mb-2 flex flex-col gap-2 pb-1">
          <div className="mx-auto h-1.5 w-12 rounded-full bg-muted" />
          <MobileSettingsHeader
            title={mobileHeaderTitle}
            canGoBack={mobileView !== "overview"}
            onBack={() => handleMobileNavigate("overview")}
            onClose={handleClose}
            backLabel={t("library.mobile.back")}
            closeLabel={t("common.cancel")}
          />
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4">
          {mobileView === "overview" ? (
            <MobileSettingsOverview
              sidebarItems={sidebarItems}
              onNavigate={handleMobileNavigate}
              accountGroupTitle={t("settings.sidebar.account")}
              generalGroupTitle={t("settings.generalSettings")}
              helpGroupTitle={t("settings.getHelp")}
              backendLabel={t("settings.backend")}
              backendValue={backend}
              backendOptions={backendOptions}
              onBackendChange={(value) => setBackend(value as BackendOption)}
              themeLabel={t("settings.theme")}
              themeValue={mode}
              themeOptions={themeOptions}
              onThemeChange={setMode}
              languageLabel={t("settings.language")}
              languageValue={currentLanguage}
              languageOptions={languageOptions}
              onLanguageChange={changeLanguage}
              helpLabel={t("settings.getHelp")}
              logoutLabel={t("userMenu.logout")}
              onOpenHelp={handleHelp}
              onLogout={handleLogout}
            />
          ) : (
            renderMobileSecondary()
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

interface MobileSettingsOverviewProps {
  sidebarItems: SettingsSidebarItem[];
  onNavigate: (view: MobileView) => void;
  accountGroupTitle: string;
  generalGroupTitle: string;
  helpGroupTitle: string;
  backendLabel: string;
  backendValue: BackendOption;
  backendOptions: SettingOption[];
  onBackendChange: (value: BackendOption) => void;
  themeLabel: string;
  themeValue: "light" | "dark";
  themeOptions: SettingOption[];
  onThemeChange: (value: "light" | "dark") => void;
  languageLabel: string;
  languageValue: string;
  languageOptions: SettingOption[];
  onLanguageChange: (value: string) => void;
  helpLabel: string;
  logoutLabel: string;
  onOpenHelp: () => void;
  onLogout: () => void;
}

function MobileSettingsOverview({
  sidebarItems,
  onNavigate,
  accountGroupTitle,
  generalGroupTitle,
  helpGroupTitle,
  backendLabel,
  backendValue,
  backendOptions,
  onBackendChange,
  themeLabel,
  themeValue,
  themeOptions,
  onThemeChange,
  languageLabel,
  languageValue,
  languageOptions,
  onLanguageChange,
  helpLabel,
  logoutLabel,
  onOpenHelp,
  onLogout,
}: MobileSettingsOverviewProps) {
  const accountItems = sidebarItems.filter((item) => item.id !== "models");
  const modelItems = sidebarItems.filter((item) => item.id === "models");

  return (
    <div className="flex-1 space-y-5 overflow-y-auto pb-2">
      <SettingCard title={accountGroupTitle}>
        {accountItems.map((item) => (
          <SettingNavRow
            key={item.id}
            icon={item.icon}
            title={item.label}
            onClick={() => onNavigate(item.id)}
          />
        ))}
      </SettingCard>

      <SettingCard title={generalGroupTitle}>
        {modelItems.map((item) => (
          <SettingNavRow
            key={item.id}
            icon={item.icon}
            title={item.label}
            onClick={() => onNavigate(item.id)}
          />
        ))}
        <SettingSelectRow
          icon={SlidersHorizontal}
          title={backendLabel}
          value={backendValue}
          options={backendOptions}
          onChange={(value) => onBackendChange(value as BackendOption)}
        />
        <SettingSelectRow
          icon={Palette}
          title={themeLabel}
          value={themeValue}
          options={themeOptions}
          onChange={(value) => onThemeChange(value as "light" | "dark")}
        />
        <SettingSelectRow
          icon={Languages}
          title={languageLabel}
          value={languageValue}
          options={languageOptions}
          onChange={onLanguageChange}
        />
      </SettingCard>

      <SettingCard title={helpGroupTitle}>
        <SettingNavRow
          icon={HelpCircle}
          title={helpLabel}
          onClick={onOpenHelp}
        />
        <SettingNavRow
          icon={LogOut}
          title={logoutLabel}
          destructive
          showChevron={false}
          onClick={onLogout}
        />
      </SettingCard>
    </div>
  );
}

interface MobileSettingsHeaderProps {
  title: string;
  canGoBack: boolean;
  onBack: () => void;
  onClose: () => void;
  backLabel: string;
  closeLabel: string;
}

function MobileSettingsHeader({
  title,
  canGoBack,
  onBack,
  onClose,
  backLabel,
  closeLabel,
}: MobileSettingsHeaderProps) {
  return (
    <div className="mb-2 flex items-center justify-between gap-4">
      {canGoBack ? (
        <Button
          variant="ghost"
          size="icon"
          className="size-10 rounded-full border border-border/40 bg-card/80 text-foreground"
          onClick={onBack}
          aria-label={backLabel}
          data-prevent-drag="true"
        >
          <ChevronLeft className="size-5" />
          <span className="sr-only">{backLabel}</span>
        </Button>
      ) : (
        <div className="size-10" />
      )}

      <div className="text-center">
        <p className="text-lg font-semibold text-foreground">{title}</p>
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="size-10 rounded-full border border-border/40 bg-card/80 text-foreground"
        onClick={onClose}
        aria-label={closeLabel}
        data-prevent-drag="true"
      >
        <X className="size-4" />
        <span className="sr-only">{closeLabel}</span>
      </Button>
    </div>
  );
}

interface SettingCardProps {
  title: string;
  children: React.ReactNode;
}

function SettingCard({ title, children }: SettingCardProps) {
  const items = React.Children.toArray(children);

  return (
    <section className="space-y-2">
      <p className="text-xs font-semibold text-muted-foreground">{title}</p>
      <div className="rounded-3xl border border-border/50 bg-card/70 shadow-[var(--shadow-lg)]">
        {items.map((child, index) => (
          <div
            key={index}
            className={cn(index > 0 && "border-t border-border/40")}
          >
            {child}
          </div>
        ))}
      </div>
    </section>
  );
}

interface SettingNavRowProps {
  icon: LucideIcon;
  title: string;
  value?: string;
  onClick?: () => void;
  showChevron?: boolean;
  destructive?: boolean;
}

function SettingNavRow({
  icon: Icon,
  title,
  value,
  onClick,
  showChevron = true,
  destructive = false,
}: SettingNavRowProps) {
  const isInteractive = Boolean(onClick);

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!isInteractive}
      className={cn(
        "flex w-full items-center gap-3 px-4 py-4 text-left transition-colors",
        destructive
          ? "text-destructive hover:bg-destructive/10"
          : "text-foreground hover:bg-foreground/5",
        !isInteractive && "cursor-default opacity-80",
      )}
    >
      <div
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-2xl bg-muted/70 text-muted-foreground",
          destructive && "bg-destructive/10 text-destructive",
        )}
      >
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-base font-medium",
            destructive && "text-destructive",
          )}
        >
          {title}
        </p>
      </div>
      {value ? (
        <span
          className={cn(
            "max-w-[40%] truncate text-sm",
            destructive ? "text-destructive" : "text-muted-foreground",
          )}
        >
          {value}
        </span>
      ) : null}
      {showChevron ? (
        <ChevronRight className="size-4 text-muted-foreground" />
      ) : null}
    </button>
  );
}

interface SettingSelectRowProps {
  icon: LucideIcon;
  title: string;
  value: string;
  options: SettingOption[];
  onChange: (value: string) => void;
}

function SettingSelectRow({
  icon: Icon,
  title,
  value,
  options,
  onChange,
}: SettingSelectRowProps) {
  return (
    <div className="flex w-full items-center gap-3 px-4 py-4 text-left">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-muted/70 text-muted-foreground">
        <Icon className="size-4" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <p className="text-base font-medium text-foreground">{title}</p>
      </div>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="min-w-[140px] rounded-2xl border border-border/60 bg-background/80 text-foreground">
          <SelectValue placeholder={title} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
