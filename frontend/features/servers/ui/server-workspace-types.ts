import type {
  ServerChannelItem,
  ServerConversationMessage,
} from "@/features/servers/model/types";

export type ColleagueSelection =
  | { kind: "agent"; id: string }
  | { kind: "human"; id: number };

export type WorkspaceMode =
  | "search"
  | "inbox"
  | "colleagues"
  | "tasks"
  | "conversation";
export type ConversationTab = "chat";
export type DrawerState =
  | { type: "none" }
  | { type: "thread"; channelId: string; rootMessageId: string }
  | { type: "artifacts" }
  | { type: "execution"; sessionId: string }
  | { type: "agent"; agentId?: string | null }
  | { type: "colleague"; selection?: ColleagueSelection | null };

export type FeedItem = {
  channel: ServerChannelItem;
  message: ServerConversationMessage;
};
