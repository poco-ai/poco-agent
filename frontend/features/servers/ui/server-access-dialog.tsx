"use client";

import * as React from "react";
import { Copy, Plus, RefreshCw, UserPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type {
  ServerInviteItem,
  ServerItem,
} from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";

export function ServerAccessDialog({
  open,
  server,
  invites,
  isWorking,
  canCreateInvite,
  onOpenChange,
  onCreateServer,
  onAcceptInvite,
  onCreateInvite,
  onCopyInvite,
}: {
  open: boolean;
  server: ServerItem | null;
  invites: ServerInviteItem[];
  isWorking: boolean;
  canCreateInvite: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateServer: (name: string) => void;
  onAcceptInvite: (token: string) => void;
  onCreateInvite: () => void;
  onCopyInvite: (token: string) => void;
}) {
  const { t } = useT("translation");
  const [serverName, setServerName] = React.useState("");
  const [inviteToken, setInviteToken] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setServerName("");
      setInviteToken("");
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("conversationView.serverAccess.title")}</DialogTitle>
          <DialogDescription>
            {t("conversationView.serverAccess.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          <section className="space-y-3 rounded-md border border-border bg-card p-4">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {t("conversationView.serverAccess.createTitle")}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("conversationView.serverAccess.createDescription")}
              </p>
            </div>
            <Input
              value={serverName}
              onChange={(event) => setServerName(event.target.value)}
              placeholder={t("conversationView.serverAccess.serverName")}
            />
            <Button
              type="button"
              size="sm"
              onClick={() => onCreateServer(serverName)}
              disabled={isWorking || !serverName.trim()}
            >
              <Plus className="size-4" />
              {t("conversationView.serverAccess.createAction")}
            </Button>
          </section>

          <section className="space-y-3 rounded-md border border-border bg-card p-4">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {t("conversationView.serverAccess.joinTitle")}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("conversationView.serverAccess.joinDescription")}
              </p>
            </div>
            <Input
              value={inviteToken}
              onChange={(event) => setInviteToken(event.target.value)}
              placeholder={t("conversationView.serverAccess.inviteKey")}
            />
            <Button
              type="button"
              size="sm"
              onClick={() => onAcceptInvite(inviteToken)}
              disabled={isWorking || !inviteToken.trim()}
            >
              <UserPlus className="size-4" />
              {t("conversationView.serverAccess.joinAction")}
            </Button>
          </section>
        </div>

        <section className="space-y-3 rounded-md border border-border bg-card p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {t("conversationView.serverAccess.invitesTitle")}
              </p>
              <p className="text-xs text-muted-foreground">
                {server
                  ? t("conversationView.serverAccess.invitesDescription", {
                      server: server.name,
                    })
                  : t("conversationView.serverAccess.noServer")}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCreateInvite}
              disabled={isWorking || !server || !canCreateInvite}
              title={
                canCreateInvite
                  ? undefined
                  : t("conversationView.serverAccess.invitePermissionHint")
              }
            >
              <RefreshCw className="size-4" />
              {t("conversationView.serverAccess.generateInvite")}
            </Button>
          </div>
          {!canCreateInvite ? (
            <p className="text-xs text-muted-foreground">
              {t("conversationView.serverAccess.invitePermissionHint")}
            </p>
          ) : null}
          <div className="space-y-2">
            {invites.length > 0 ? (
              invites.map((invite) => (
                <div
                  key={invite.id}
                  className="flex items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs text-foreground">
                      {invite.token}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t("conversationView.serverAccess.inviteMeta", {
                        used: invite.usedCount,
                        max: invite.maxUses,
                      })}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => onCopyInvite(invite.token)}
                    aria-label={t("conversationView.serverAccess.copyInvite")}
                  >
                    <Copy className="size-4" />
                  </Button>
                </div>
              ))
            ) : (
              <div className="rounded-md border border-dashed border-border px-3 py-8 text-center text-sm text-muted-foreground">
                {t("conversationView.serverAccess.noInvites")}
              </div>
            )}
          </div>
        </section>
      </DialogContent>
    </Dialog>
  );
}
