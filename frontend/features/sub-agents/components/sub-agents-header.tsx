"use client";

import { ArrowLeft, Plus } from "lucide-react";
import { useRouter } from "next/navigation";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { useAppShell } from "@/components/shared/app-shell-context";
import { HeaderSearchInput } from "@/components/shared/header-search-input";

interface SubAgentsHeaderProps {
  onAddClick?: () => void;
  searchQuery: string;
  onSearchChange: (value: string) => void;
}

export function SubAgentsHeader({
  onAddClick,
  searchQuery,
  onSearchChange,
}: SubAgentsHeaderProps) {
  const { t } = useT("translation");
  const router = useRouter();
  const { lng } = useAppShell();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/50 bg-background/50 px-6 backdrop-blur-sm sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push(`/${lng}/capabilities`)}
          className="mr-2"
        >
          <ArrowLeft className="size-5" />
        </Button>
        <span className="text-lg font-bold tracking-tight">
          {t("library.subAgents.header.title", "子代理")}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <HeaderSearchInput
          value={searchQuery}
          onChange={onSearchChange}
          placeholder={t(
            "library.subAgents.searchPlaceholder",
            "搜索子代理...",
          )}
        />
        <Button
          variant="ghost"
          size="sm"
          className="gap-2"
          onClick={onAddClick}
        >
          <Plus className="size-4" />
          {t("library.subAgents.header.add", "添加子代理")}
        </Button>
      </div>
    </header>
  );
}
