"use client";

import * as React from "react";
import { Loader2, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  ServerChannelItem,
  ServerItem,
} from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";

interface ShareToChannelDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  servers: ServerItem[];
  channels: ServerChannelItem[];
  selectedServerId: string;
  onSelectedServerIdChange: (serverId: string) => void;
  selectedChannelId: string;
  onSelectedChannelIdChange: (channelId: string) => void;
  isSharing: boolean;
  onShare: () => void | Promise<void>;
}

export function ShareToChannelDialog({
  open,
  onOpenChange,
  servers,
  channels,
  selectedServerId,
  onSelectedServerIdChange,
  selectedChannelId,
  onSelectedChannelIdChange,
  isSharing,
  onShare,
}: ShareToChannelDialogProps) {
  const { t } = useT("translation");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogTitle>{t("chat.shareToChannel")}</DialogTitle>
        <DialogDescription>
          {t("chat.shareToChannelDescription")}
        </DialogDescription>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              {t("chat.shareServer")}
            </label>
            <Select
              value={selectedServerId}
              onValueChange={(value) => {
                onSelectedServerIdChange(value);
                onSelectedChannelIdChange("");
              }}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder={t("chat.shareServer")} />
              </SelectTrigger>
              <SelectContent>
                {servers.map((server) => (
                  <SelectItem key={server.id} value={server.id}>
                    {server.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              {t("chat.shareChannel")}
            </label>
            <Select
              value={selectedChannelId}
              onValueChange={onSelectedChannelIdChange}
              disabled={!selectedServerId || channels.length === 0}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder={t("chat.shareChannel")} />
              </SelectTrigger>
              <SelectContent>
                {channels.map((channel) => (
                  <SelectItem key={channel.id} value={channel.id}>
                    #{channel.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSharing}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            onClick={() => void onShare()}
            disabled={!selectedServerId || !selectedChannelId || isSharing}
          >
            {isSharing ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
            {t("chat.shareToChannel")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
