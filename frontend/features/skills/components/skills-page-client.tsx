"use client";

import { useState } from "react";
import { SkillsHeader } from "@/features/skills/components/skills-header";
import {
  MOCK_PRESETS,
  MOCK_INSTALLS,
  SkillsGrid,
} from "@/features/skills/components/skills-grid";

import type { SkillPreset, UserSkillInstall } from "@/features/skills/types";
import { toast } from "sonner";
import { CheckCircle2, CircleOff } from "lucide-react";
import * as React from "react";

interface SkillsPageClientProps {
  initialPresets?: SkillPreset[];
  initialInstalls?: UserSkillInstall[];
}

export function SkillsPageClient({
  initialPresets = [],
  initialInstalls = [],
}: SkillsPageClientProps) {
  const [loadingId, setLoadingId] = useState<number | null>(null);

  // State for presets and installs
  const [presets] = useState<SkillPreset[]>(
    initialPresets.length > 0 ? initialPresets : MOCK_PRESETS,
  );
  const [installs, setInstalls] = useState<UserSkillInstall[]>(
    initialInstalls.length > 0 ? initialInstalls : MOCK_INSTALLS,
  );

  const handleToggleEnabled = async (installId: number, enabled: boolean) => {
    const install = installs.find((i: UserSkillInstall) => i.id === installId);
    if (!install) return;

    // Find the associated preset name for the toast
    const preset = presets.find((p: SkillPreset) => p.id === install.preset_id);
    const skillName = preset?.display_name || preset?.name || "Skill";

    setLoadingId(installId);

    // Optimistic update
    setInstalls((prev: UserSkillInstall[]) =>
      prev.map((i: UserSkillInstall) =>
        i.id === installId ? { ...i, enabled } : i,
      ),
    );

    try {
      // Simulate API call
      await new Promise((r) => setTimeout(r, 500));

      toast.success(`${skillName} Skill ${enabled ? "已启用" : "已停用"}`, {
        icon: enabled
          ? React.createElement(CheckCircle2, {
              className: "size-4 text-foreground",
            })
          : React.createElement(CircleOff, {
              className: "size-4 text-muted-foreground",
            }),
      });

      // Trigger success haptic feedback
      if (typeof window !== "undefined" && "vibrate" in navigator) {
        navigator.vibrate(50);
      }
    } catch {
      // Rollback
      setInstalls((prev: UserSkillInstall[]) =>
        prev.map((i: UserSkillInstall) =>
          i.id === installId ? { ...i, enabled: !enabled } : i,
        ),
      );
      toast.error("操作失败");
    } finally {
      setLoadingId(null);
    }
  };

  // TODO: Connect to real API
  const handleInstall = async (presetId: number) => {
    const preset = presets.find((p: SkillPreset) => p.id === presetId);
    const skillName = preset?.display_name || preset?.name || "Skill";

    setLoadingId(presetId);

    try {
      // Simulate API call
      await new Promise((r) => setTimeout(r, 800));

      const newInstall: UserSkillInstall = {
        id: Math.floor(Math.random() * 10000),
        user_id: "user1",
        preset_id: presetId,
        enabled: true,
        overrides: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      setInstalls((prev) => [...prev, newInstall]);

      toast.success(`${skillName} Skill 已安装`, {
        icon: React.createElement(CheckCircle2, {
          className: "size-4 text-foreground",
        }),
      });

      if (typeof window !== "undefined" && "vibrate" in navigator) {
        navigator.vibrate(50);
      }
    } catch {
      toast.error("安装失败");
    } finally {
      setLoadingId(null);
    }
  };

  const handleUninstall = async (installId: number) => {
    const install = installs.find((i: UserSkillInstall) => i.id === installId);
    const preset = presets.find(
      (p: SkillPreset) => p.id === install?.preset_id,
    );
    const skillName = preset?.display_name || preset?.name || "Skill";

    setLoadingId(installId);

    try {
      // Simulate API call
      await new Promise((r) => setTimeout(r, 800));

      setInstalls((prev) => prev.filter((i) => i.id !== installId));

      toast.success(`${skillName} Skill 已卸载`);

      if (typeof window !== "undefined" && "vibrate" in navigator) {
        navigator.vibrate(50);
      }
    } catch {
      toast.error("卸载失败");
    } finally {
      setLoadingId(null);
    }
  };

  const handleUpdate = async (installId: number) => {
    setLoadingId(installId);
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1000));
    console.log("Update install:", installId);
    setLoadingId(null);
  };

  const handleUploadToPreset = async (installId: number) => {
    setLoadingId(installId);
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1000));
    console.log("Upload to preset:", installId);
    setLoadingId(null);
  };

  return (
    <>
      <SkillsHeader />

      <div className="flex flex-1 flex-col px-6 py-6 overflow-auto">
        <div className="w-full max-w-4xl mx-auto">
          <SkillsGrid
            presets={presets}
            installs={installs}
            loadingId={loadingId}
            onInstall={handleInstall}
            onUninstall={handleUninstall}
            onUpdate={handleUpdate}
            onUploadToPreset={handleUploadToPreset}
            onToggleEnabled={handleToggleEnabled}
          />
        </div>
      </div>
    </>
  );
}
