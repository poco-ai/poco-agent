"use client";

import * as React from "react";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";

import { SectionCard } from "./shared";

interface AdminCatalogShellProps {
  title: string;
  description: string;
  summary: string;
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder: string;
  createLabel?: string;
  onCreate?: () => void;
  children: React.ReactNode;
}

export function AdminCatalogShell({
  title,
  description,
  summary,
  searchValue,
  onSearchChange,
  searchPlaceholder,
  createLabel,
  onCreate,
  children,
}: AdminCatalogShellProps) {
  return (
    <SectionCard title={title} description={description}>
      <div className="space-y-6">
        <div className="rounded-xl bg-muted/50 px-5 py-3">
          <div className="flex flex-wrap items-center gap-3 md:justify-between">
            <p className="text-sm text-muted-foreground">{summary}</p>
            <HeaderSearchInput
              value={searchValue}
              onChange={onSearchChange}
              placeholder={searchPlaceholder}
              className="w-full md:w-64"
            />
          </div>
        </div>
        <div className="space-y-3">
          {createLabel && onCreate ? (
            <CapabilityCreateCard label={createLabel} onClick={onCreate} />
          ) : null}
          {children}
        </div>
      </div>
    </SectionCard>
  );
}
