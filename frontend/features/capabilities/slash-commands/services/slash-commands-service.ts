import { apiClient, API_ENDPOINTS } from "@/lib/api-client";
import type {
  SlashCommand,
  SlashCommandCreateInput,
  SlashCommandSuggestion,
  SlashCommandUpdateInput,
} from "@/features/capabilities/slash-commands/types";

export const SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT =
  "poco:slash-command-suggestions-invalidated";

function emitSlashCommandSuggestionsInvalidated(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT));
}

export const slashCommandsService = {
  list: async (options?: { revalidate?: number }): Promise<SlashCommand[]> => {
    return apiClient.get<SlashCommand[]>(API_ENDPOINTS.slashCommands, {
      next: { revalidate: options?.revalidate },
    });
  },

  listSuggestions: async (options?: {
    revalidate?: number;
    cacheBust?: string | number;
  }): Promise<SlashCommandSuggestion[]> => {
    const endpoint =
      options?.cacheBust !== undefined && options?.cacheBust !== null
        ? `${API_ENDPOINTS.slashCommandSuggestions}?_t=${encodeURIComponent(String(options.cacheBust))}`
        : API_ENDPOINTS.slashCommandSuggestions;
    return apiClient.get<SlashCommandSuggestion[]>(endpoint, {
      cache: "no-store",
      next: { revalidate: options?.revalidate },
    });
  },

  get: async (
    commandId: number,
    options?: { revalidate?: number },
  ): Promise<SlashCommand> => {
    return apiClient.get<SlashCommand>(API_ENDPOINTS.slashCommand(commandId), {
      next: { revalidate: options?.revalidate },
    });
  },

  create: async (input: SlashCommandCreateInput): Promise<SlashCommand> => {
    const created = await apiClient.post<SlashCommand>(
      API_ENDPOINTS.slashCommands,
      input,
    );
    emitSlashCommandSuggestionsInvalidated();
    return created;
  },

  update: async (
    commandId: number,
    input: SlashCommandUpdateInput,
  ): Promise<SlashCommand> => {
    const updated = await apiClient.patch<SlashCommand>(
      API_ENDPOINTS.slashCommand(commandId),
      input,
    );
    emitSlashCommandSuggestionsInvalidated();
    return updated;
  },

  remove: async (commandId: number): Promise<Record<string, unknown>> => {
    const removed = await apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.slashCommand(commandId),
    );
    emitSlashCommandSuggestionsInvalidated();
    return removed;
  },
};
