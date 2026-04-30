"use client";

import * as React from "react";
import {
  Bot,
  Box,
  Command as CommandIcon,
  FileText,
  Package,
  Shield,
  Puzzle,
  KeySquare,
  Plug,
  Server,
  SlidersHorizontal,
  Users,
} from "lucide-react";

import { CapabilitiesSidebar } from "@/features/capabilities/components/capabilities-sidebar";
import { CapabilitiesLibraryHeader } from "@/features/capabilities/components/capabilities-library-header";
import type { CapabilityView } from "@/features/capabilities/hooks/use-capability-views";
import { AdminEnvVarsSection } from "@/features/settings/components/tabs/admin/env-vars-section";
import { RuntimeEnvPolicySection } from "@/features/settings/components/tabs/admin/runtime-env-policy-section";
import { AdminMcpSection } from "@/features/settings/components/tabs/admin/mcp-section";
import { AdminModelConfigSection } from "@/features/settings/components/tabs/admin/model-config-section";
import { AdminPluginsSection } from "@/features/settings/components/tabs/admin/plugins-section";
import { AdminPresetsSection } from "@/features/settings/components/tabs/admin/presets-section";
import { AdminSlashCommandsSection } from "@/features/settings/components/tabs/admin/slash-commands-section";
import { AdminSubAgentsSection } from "@/features/settings/components/tabs/admin/sub-agents-section";
import { AdminClaudeMdSection } from "@/features/settings/components/tabs/admin/claude-md-section";
import { AdminSkillsSection } from "@/features/settings/components/tabs/admin/skills-section";
import { AdminUsersSection } from "@/features/settings/components/tabs/admin/users-section";
import { SectionCard } from "@/features/settings/components/tabs/admin/shared";
import { useAdminConsole } from "@/features/settings/hooks/use-admin-console";
import { useT } from "@/lib/i18n/client";

const EMPTY_COMPONENT = () => null;

export function AdminSettingsTab() {
  const { t } = useT("translation");
  const [activeViewId, setActiveViewId] = React.useState("overview");
  const {
    envVars,
    users,
    skills,
    mcpServers,
    plugins,
    slashCommands,
    subAgents,
    presets,
    presetVisuals,
    systemClaudeMd,
    modelConfig,
    runtimeEnvPolicy,
    isLoadingScope,
    hasErrorScope,
    isSavingScope,
    refreshScope,
    saveModelConfig,
    saveRuntimeEnvPolicy,
    createEnvVar,
    updateEnvVar,
    deleteEnvVar,
    updateSkill,
    deleteSkill,
    createMcpServer,
    updateMcpServer,
    deleteMcpServer,
    createPlugin,
    updatePlugin,
    deletePlugin,
    createSlashCommand,
    updateSlashCommand,
    deleteSlashCommand,
    createSubAgent,
    updateSubAgent,
    deleteSubAgent,
    createPreset,
    updatePreset,
    deletePreset,
    saveSystemClaudeMd,
    deleteSystemClaudeMd,
    updateUserRole,
  } = useAdminConsole();

  const sectionSaving = {
    modelConfig: isSavingScope("modelConfig"),
    envVars: isSavingScope("envVars"),
    runtimeEnvPolicy: isSavingScope("runtimeEnvPolicy"),
    skills: isSavingScope("skills"),
    mcp: isSavingScope("mcp"),
    plugins: isSavingScope("plugins"),
    slashCommands: isSavingScope("slashCommands"),
    subAgents: isSavingScope("subAgents"),
    presets: isSavingScope("presets"),
    claudeMd: isSavingScope("claudeMd"),
    users: isSavingScope("users"),
  };

  const sectionLoading = {
    modelConfig: isLoadingScope("modelConfig"),
    envVars: isLoadingScope("envVars"),
    runtimeEnvPolicy: isLoadingScope("runtimeEnvPolicy"),
    skills: isLoadingScope("skills"),
    mcp: isLoadingScope("mcp"),
    plugins: isLoadingScope("plugins"),
    slashCommands: isLoadingScope("slashCommands"),
    subAgents: isLoadingScope("subAgents"),
    presets: isLoadingScope("presets"),
    claudeMd: isLoadingScope("claudeMd"),
    users: isLoadingScope("users"),
  };

  const sectionError = {
    modelConfig: hasErrorScope("modelConfig"),
    envVars: hasErrorScope("envVars"),
    runtimeEnvPolicy: hasErrorScope("runtimeEnvPolicy"),
    skills: hasErrorScope("skills"),
    mcp: hasErrorScope("mcp"),
    plugins: hasErrorScope("plugins"),
    slashCommands: hasErrorScope("slashCommands"),
    subAgents: hasErrorScope("subAgents"),
    presets: hasErrorScope("presets"),
    claudeMd: hasErrorScope("claudeMd"),
    users: hasErrorScope("users"),
  };

  const views = React.useMemo<CapabilityView[]>(
    () => [
      {
        id: "overview",
        label: t("settings.admin.navOverview"),
        description: t("settings.admin.navOverviewDescription"),
        icon: Shield,
        group: "featured",
        component: EMPTY_COMPONENT,
      },
      {
        id: "models",
        label: t("settings.admin.navModels"),
        description: t("settings.admin.modelConfigDescription"),
        icon: SlidersHorizontal,
        group: "secondary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "envVars",
        label: t("settings.admin.navEnvVars"),
        description: t("settings.admin.envDescription"),
        icon: KeySquare,
        group: "secondary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "runtimeEnvPolicy",
        label: t("settings.admin.navRuntimeEnvPolicy"),
        description: t("settings.admin.runtimeEnvPolicyDescription"),
        icon: Shield,
        group: "secondary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "skills",
        label: t("settings.admin.navSkills"),
        description: t("settings.admin.skillsDescription"),
        icon: Puzzle,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "mcp",
        label: t("settings.admin.navMcp"),
        description: t("settings.admin.mcpDescription"),
        icon: Server,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "plugins",
        label: t("settings.admin.navPlugins"),
        description: t("settings.admin.pluginsDescription"),
        icon: Plug,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "slashCommands",
        label: t("settings.admin.navSlashCommands"),
        description: t("settings.admin.slashCommandsDescription"),
        icon: CommandIcon,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "subAgents",
        label: t("settings.admin.navSubAgents"),
        description: t("settings.admin.subAgentsDescription"),
        icon: Bot,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "presets",
        label: t("settings.admin.navPresets"),
        description: t("settings.admin.presetsDescription"),
        icon: Package,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "claudeMd",
        label: t("settings.admin.navPersonalization"),
        description: t("settings.admin.claudeMdDescription"),
        icon: FileText,
        group: "primary",
        component: EMPTY_COMPONENT,
      },
      {
        id: "users",
        label: t("settings.admin.navUsers"),
        description: t("settings.admin.usersDescription"),
        icon: Users,
        group: "tertiary",
        component: EMPTY_COMPONENT,
      },
    ],
    [t],
  );

  const activeView = (() => {
    switch (activeViewId) {
      case "overview":
        return (
          <SectionCard
            title={t("settings.admin.title")}
            description={t("settings.admin.description")}
          >
            <div className="grid gap-3 md:grid-cols-3">
              <AdminSummaryCard
                icon={Box}
                label={t("settings.admin.summaryResources")}
                value={String(
                  skills.length +
                    mcpServers.length +
                    plugins.length +
                    slashCommands.length +
                    subAgents.length +
                    presets.length,
                )}
              />
              <AdminSummaryCard
                icon={Users}
                label={t("settings.admin.summaryUsers")}
                value={String(users.length)}
              />
              <AdminSummaryCard
                icon={KeySquare}
                label={t("settings.admin.summaryEnvVars")}
                value={String(envVars.length)}
              />
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-dashed border-border px-3 py-2 text-sm text-muted-foreground">
              <Shield className="size-4" />
              <span>{t("settings.admin.scopeHint")}</span>
            </div>
          </SectionCard>
        );
      case "models":
        return (
          <AdminModelConfigSection
            isLoading={sectionLoading.modelConfig}
            hasError={sectionError.modelConfig}
            isSaving={sectionSaving.modelConfig}
            modelConfig={modelConfig}
            onRetry={() => refreshScope("modelConfig")}
            onSave={saveModelConfig}
          />
        );
      case "envVars":
        return (
          <AdminEnvVarsSection
            envVars={envVars}
            runtimeEnvPolicy={runtimeEnvPolicy}
            isLoading={sectionLoading.envVars}
            hasError={sectionError.envVars}
            isSaving={sectionSaving.envVars}
            onRefresh={() => refreshScope("envVars")}
            onRetry={() => refreshScope("envVars")}
            onCreate={createEnvVar}
            onUpdate={updateEnvVar}
            onDelete={deleteEnvVar}
          />
        );
      case "runtimeEnvPolicy":
        return (
          <RuntimeEnvPolicySection
            policy={runtimeEnvPolicy}
            isLoading={sectionLoading.runtimeEnvPolicy}
            hasError={sectionError.runtimeEnvPolicy}
            isSaving={sectionSaving.runtimeEnvPolicy}
            onRefresh={() => refreshScope("runtimeEnvPolicy")}
            onRetry={() => refreshScope("runtimeEnvPolicy")}
            onSave={saveRuntimeEnvPolicy}
          />
        );
      case "skills":
        return (
          <AdminSkillsSection
            isLoading={sectionLoading.skills}
            hasError={sectionError.skills}
            skills={skills}
            onRetry={() => refreshScope("skills")}
            onUpdate={updateSkill}
            onDelete={deleteSkill}
          />
        );
      case "mcp":
        return (
          <AdminMcpSection
            isLoading={sectionLoading.mcp}
            hasError={sectionError.mcp}
            isSaving={sectionSaving.mcp}
            mcpServers={mcpServers}
            onRetry={() => refreshScope("mcp")}
            onCreate={createMcpServer}
            onUpdate={updateMcpServer}
            onDelete={deleteMcpServer}
          />
        );
      case "plugins":
        return (
          <AdminPluginsSection
            isLoading={sectionLoading.plugins}
            hasError={sectionError.plugins}
            isSaving={sectionSaving.plugins}
            plugins={plugins}
            onRetry={() => refreshScope("plugins")}
            onCreate={createPlugin}
            onUpdate={updatePlugin}
            onDelete={deletePlugin}
          />
        );
      case "slashCommands":
        return (
          <AdminSlashCommandsSection
            isLoading={sectionLoading.slashCommands}
            hasError={sectionError.slashCommands}
            isSaving={sectionSaving.slashCommands}
            commands={slashCommands}
            onRetry={() => refreshScope("slashCommands")}
            onCreate={createSlashCommand}
            onUpdate={updateSlashCommand}
            onDelete={deleteSlashCommand}
          />
        );
      case "subAgents":
        return (
          <AdminSubAgentsSection
            isLoading={sectionLoading.subAgents}
            hasError={sectionError.subAgents}
            isSaving={sectionSaving.subAgents}
            subAgents={subAgents}
            onRetry={() => refreshScope("subAgents")}
            onCreate={createSubAgent}
            onUpdate={updateSubAgent}
            onDelete={deleteSubAgent}
          />
        );
      case "presets":
        return (
          <AdminPresetsSection
            isLoading={sectionLoading.presets}
            hasError={sectionError.presets}
            isSaving={sectionSaving.presets}
            presets={presets}
            onRetry={() => refreshScope("presets")}
            skills={skills}
            mcpServers={mcpServers}
            plugins={plugins}
            presetVisuals={presetVisuals}
            onCreate={createPreset}
            onUpdate={updatePreset}
            onDelete={deletePreset}
          />
        );
      case "claudeMd":
        return (
          <AdminClaudeMdSection
            isLoading={sectionLoading.claudeMd}
            hasError={sectionError.claudeMd}
            isSaving={sectionSaving.claudeMd}
            settings={systemClaudeMd}
            onRetry={() => refreshScope("claudeMd")}
            onSave={saveSystemClaudeMd}
            onDelete={deleteSystemClaudeMd}
          />
        );
      default:
        return (
          <AdminUsersSection
            isLoading={sectionLoading.users}
            hasError={sectionError.users}
            isSaving={sectionSaving.users}
            users={users}
            onRetry={() => refreshScope("users")}
            onUpdateRole={updateUserRole}
          />
        );
    }
  })();

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <CapabilitiesLibraryHeader
        title={t("settings.admin.title")}
        subtitle={t("settings.admin.pageSubtitle")}
        icon={Shield}
      />
      <div className="hidden min-h-0 flex-1 md:grid md:grid-cols-[240px_minmax(0,1fr)]">
        <CapabilitiesSidebar
          views={views}
          activeViewId={activeViewId}
          onSelect={setActiveViewId}
        />
        <main className="min-h-0 overflow-y-auto">
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium text-foreground">
                {t("settings.admin.systemScopeBadge")}
              </span>
              <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                {t("settings.admin.adminOnlyBadge")}
              </span>
            </div>
            {activeView}
          </div>
        </main>
      </div>
      <div className="flex min-h-0 flex-1 flex-col md:hidden">
        <CapabilitiesSidebar
          views={views}
          activeViewId={activeViewId}
          onSelect={setActiveViewId}
        />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium text-foreground">
                {t("settings.admin.systemScopeBadge")}
              </span>
              <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                {t("settings.admin.adminOnlyBadge")}
              </span>
            </div>
            {activeView}
          </div>
        </main>
      </div>
    </div>
  );
}

function AdminSummaryCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-muted/20 p-4">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          <Icon className="size-4" />
        </div>
        <div>
          <div className="text-2xl font-semibold tracking-tight">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </div>
    </div>
  );
}
