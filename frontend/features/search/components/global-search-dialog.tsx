"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { FileText, Folder, MessageSquare, Loader2 } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { useSearchData } from "@/features/search/hooks/use-search-data";

interface GlobalSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Global search dialog (Spotlight-like)
 * Search across tasks, projects, and messages
 */
export function GlobalSearchDialog({
  open,
  onOpenChange,
}: GlobalSearchDialogProps) {
  const { t } = useT("translation");
  const router = useRouter();
  const lng = useLanguage();
  const [searchQuery, setSearchQuery] = React.useState("");
  const { tasks, projects, messages, isLoading } = useSearchData(searchQuery, {
    enabled: open,
  });
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (!open) setSearchQuery("");
  }, [open]);

  const hasResults =
    tasks.length > 0 || projects.length > 0 || messages.length > 0;

  const handleSelect = (type: string, id: string) => {
    onOpenChange(false);

    switch (type) {
      case "task":
        router.push(lng ? `/${lng}/chat/${id}` : `/chat/${id}`);
        break;
      case "project":
        // TODO: Navigate to project page when implemented
        router.push(lng ? `/${lng}/chat/new` : `/chat/new`);
        break;
      case "message":
        // Navigate to chat page and scroll to message
        router.push(lng ? `/${lng}/chat/${id}` : `/chat/${id}`);
        break;
    }
  };

  if (!mounted) return null;

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder={t("search.placeholder")}
        value={searchQuery}
        onValueChange={setSearchQuery}
      />
      <CommandList>
        {isLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
          </div>
        ) : !hasResults && searchQuery !== "" ? (
          <CommandEmpty>{t("search.noResults")}</CommandEmpty>
        ) : null}

        {tasks.length > 0 && (
          <CommandGroup heading={t("search.tasks")}>
            {tasks.map((task) => (
              <CommandItem
                key={task.id}
                onSelect={() => handleSelect("task", task.id)}
              >
                <FileText className="size-4 text-muted-foreground" />
                <span className="flex-1">
                  {task.title || t("chat.newChat")}
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(task.timestamp).toLocaleDateString()}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {projects.length > 0 && (
          <CommandGroup heading={t("search.projects")}>
            {projects.map((project) => (
              <CommandItem
                key={project.id}
                onSelect={() => handleSelect("project", project.id)}
              >
                <Folder className="size-4 text-muted-foreground" />
                <span className="flex-1">{project.name}</span>
                {project.taskCount !== undefined && (
                  <span className="text-xs text-muted-foreground">
                    {project.taskCount} tasks
                  </span>
                )}
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {messages.length > 0 && (
          <CommandGroup heading={t("search.messages")}>
            {messages.slice(0, 5).map((message) => (
              <CommandItem
                key={message.id}
                onSelect={() => handleSelect("message", message.chatId)}
              >
                <MessageSquare className="size-4 text-muted-foreground" />
                <span className="line-clamp-1 flex-1">{message.content}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
}
