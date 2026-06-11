"use client";

import * as React from "react";
import { toast } from "sonner";

import { sessionShareApi } from "@/features/chat/api/session-share-api";
import { serversApi } from "@/features/servers";
import type {
  ServerChannelItem,
  ServerItem,
} from "@/features/servers/model/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { copyToClipboard } from "@/lib/utils/clipboard/copy-to-clipboard";

interface UseSessionShareActionsOptions {
  sessionId?: string | null;
  title?: string | null;
  logContext?: string;
}

export function useSessionShareActions({
  sessionId,
  title,
  logContext = "SessionShareActions",
}: UseSessionShareActionsOptions) {
  const { t } = useT("translation");
  const lng = useLanguage();
  const [shareToken, setShareToken] = React.useState<string | null>(null);
  const [isCreatingShare, setIsCreatingShare] = React.useState(false);
  const [shareToChannelOpen, setShareToChannelOpen] = React.useState(false);
  const [isSharingToChannel, setIsSharingToChannel] = React.useState(false);
  const [shareServers, setShareServers] = React.useState<ServerItem[]>([]);
  const [shareChannels, setShareChannels] = React.useState<ServerChannelItem[]>(
    [],
  );
  const [selectedShareServerId, setSelectedShareServerId] =
    React.useState<string>("");
  const [selectedShareChannelId, setSelectedShareChannelId] =
    React.useState<string>("");

  React.useEffect(() => {
    setShareToken(null);
    setShareToChannelOpen(false);
    setShareServers([]);
    setShareChannels([]);
    setSelectedShareServerId("");
    setSelectedShareChannelId("");
  }, [sessionId]);

  React.useEffect(() => {
    if (!shareToChannelOpen) {
      return;
    }
    let cancelled = false;
    void serversApi
      .listServers()
      .then((servers) => {
        if (cancelled) return;
        setShareServers(servers);
        setSelectedShareServerId((current) => current || servers[0]?.id || "");
      })
      .catch((error) => {
        console.error(`[${logContext}] Failed to load share servers:`, error);
        if (!cancelled) {
          toast.error(t("chat.shareLoadTargetsFailed"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [logContext, shareToChannelOpen, t]);

  React.useEffect(() => {
    if (!shareToChannelOpen || !selectedShareServerId) {
      setShareChannels([]);
      setSelectedShareChannelId("");
      return;
    }
    let cancelled = false;
    void serversApi
      .listChannels(selectedShareServerId)
      .then((channels) => {
        if (cancelled) return;
        const visibleChannels = channels.filter(
          (channel) => channel.conversationType === "channel",
        );
        setShareChannels(visibleChannels);
        setSelectedShareChannelId((current) =>
          visibleChannels.some((channel) => channel.id === current)
            ? current
            : visibleChannels[0]?.id || "",
        );
      })
      .catch((error) => {
        console.error(`[${logContext}] Failed to load share channels:`, error);
        if (!cancelled) {
          toast.error(t("chat.shareLoadTargetsFailed"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [logContext, selectedShareServerId, shareToChannelOpen, t]);

  const buildShareUrl = React.useCallback(
    (token: string) => {
      const path = lng ? `/${lng}/share/${token}` : `/share/${token}`;
      if (typeof window === "undefined") {
        return path;
      }
      return `${window.location.origin}${path}`;
    },
    [lng],
  );

  const ensureShareToken = React.useCallback(async (): Promise<string> => {
    if (!sessionId) {
      throw new Error("Session is not ready");
    }
    if (shareToken) {
      return shareToken;
    }
    setIsCreatingShare(true);
    try {
      const share = await sessionShareApi.createShare(sessionId, {
        title,
      });
      setShareToken(share.token);
      return share.token;
    } finally {
      setIsCreatingShare(false);
    }
  }, [sessionId, shareToken, title]);

  const copyShareLink = React.useCallback(async () => {
    if (!sessionId || isCreatingShare) return;
    try {
      const token = await ensureShareToken();
      const copied = await copyToClipboard(buildShareUrl(token));
      if (copied) {
        toast.success(t("chat.shareLinkCopied"));
      } else {
        toast.error(t("chat.shareCopyFailed"));
      }
    } catch (error) {
      console.error(`[${logContext}] Failed to copy share link:`, error);
      toast.error(t("chat.shareCreateFailed"));
    }
  }, [
    buildShareUrl,
    ensureShareToken,
    isCreatingShare,
    logContext,
    sessionId,
    t,
  ]);

  const shareToChannel = React.useCallback(async () => {
    if (
      !sessionId ||
      !selectedShareServerId ||
      !selectedShareChannelId ||
      isSharingToChannel
    ) {
      return;
    }
    setIsSharingToChannel(true);
    try {
      const token = await ensureShareToken();
      await sessionShareApi.shareToChannel(token, {
        serverId: selectedShareServerId,
        channelId: selectedShareChannelId,
        title,
      });
      toast.success(t("chat.shareToChannelSuccess"));
      setShareToChannelOpen(false);
    } catch (error) {
      console.error(`[${logContext}] Failed to share to channel:`, error);
      toast.error(t("chat.shareToChannelFailed"));
    } finally {
      setIsSharingToChannel(false);
    }
  }, [
    ensureShareToken,
    isSharingToChannel,
    logContext,
    selectedShareChannelId,
    selectedShareServerId,
    sessionId,
    t,
    title,
  ]);

  return {
    shareToken,
    isCreatingShare,
    shareToChannelOpen,
    setShareToChannelOpen,
    isSharingToChannel,
    shareServers,
    shareChannels,
    selectedShareServerId,
    setSelectedShareServerId,
    selectedShareChannelId,
    setSelectedShareChannelId,
    copyShareLink,
    shareToChannel,
  };
}
