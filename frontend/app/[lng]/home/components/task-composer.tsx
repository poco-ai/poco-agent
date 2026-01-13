"use client";

import * as React from "react";
import {
  ArrowUp,
  FileText,
  Figma,
  Mic,
  Plus,
  SlidersHorizontal,
} from "lucide-react";

import { useT } from "@/app/i18n/client";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";

import { MOCK_CONNECTORS } from "../model/connectors";

export function TaskComposer({
  textareaRef,
  value,
  onChange,
  onSend,
}: {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
}) {
  const { t } = useT("translation");

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      {/* 输入区域 */}
      <div className="px-4 pb-3 pt-4">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder={t("hero.placeholder")}
          className="min-h-[60px] max-h-[40vh] w-full resize-none border-0 bg-transparent dark:bg-transparent p-0 text-base shadow-none placeholder:text-muted-foreground/50 focus-visible:ring-0"
          rows={2}
        />
      </div>

      {/* 底部工具栏 */}
      <div className="flex items-center justify-between px-3 pb-3">
        {/* 左侧操作按钮 */}
        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-9 rounded-xl hover:bg-accent"
                title={t("hero.attachFile")}
              >
                <Plus className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              <DropdownMenuItem>
                <FileText className="mr-2 size-4" />
                <span>从本地文件导入</span>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Figma className="mr-2 size-4" />
                <span>从 Figma 导入</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-9 rounded-xl hover:bg-accent"
                title={t("hero.tools")}
              >
                <SlidersHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-56 max-h-64 overflow-y-auto"
            >
              {MOCK_CONNECTORS.filter((c) => c.type === "app").map(
                (connector) => (
                  <DropdownMenuItem key={connector.id}>
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-2">
                        <connector.icon className="size-4" />
                        <span>{connector.title}</span>
                      </div>
                      <span className="text-xs text-primary font-medium">
                        连接
                      </span>
                    </div>
                  </DropdownMenuItem>
                ),
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* 右侧操作按钮 */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-9 rounded-xl hover:bg-accent"
            title={t("hero.voiceInput")}
          >
            <Mic className="size-4" />
          </Button>
          <Button
            onClick={onSend}
            disabled={!value.trim()}
            size="icon"
            className="size-9 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground"
            title={t("hero.send")}
          >
            <ArrowUp className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
