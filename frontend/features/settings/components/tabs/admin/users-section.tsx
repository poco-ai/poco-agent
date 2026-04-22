import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  SectionCard,
} from "@/features/settings/components/tabs/admin/shared";
import type { UserProfile } from "@/features/user/types";
import { useT } from "@/lib/i18n/client";

interface AdminUsersSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  users: UserProfile[];
  onRetry: () => void;
  onUpdateRole: (userId: string, systemRole: "user" | "admin") => Promise<void>;
}

export function AdminUsersSection({
  isLoading,
  hasError,
  isSaving,
  users,
  onRetry,
  onUpdateRole,
}: AdminUsersSectionProps) {
  const { t } = useT("translation");

  return (
    <SectionCard
      title={t("settings.admin.usersTitle")}
      description={t("settings.admin.usersDescription")}
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <div className="space-y-2">
          {users.map((user) => (
            <ListItem
              key={user.id}
              title={user.displayName || user.email || user.id}
              description={user.email || user.id}
              badge={
                <Badge
                  variant={user.systemRole === "admin" ? "default" : "outline"}
                >
                  {user.systemRole === "admin"
                    ? t("settings.admin.roleAdmin")
                    : t("settings.admin.roleUser")}
                </Badge>
              }
            >
              <div className="flex justify-end">
                <Select
                  value={user.systemRole}
                  onValueChange={(value) =>
                    void onUpdateRole(user.id, value as "user" | "admin")
                  }
                  disabled={isSaving}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">
                      {t("settings.admin.roleUser")}
                    </SelectItem>
                    <SelectItem value="admin">
                      {t("settings.admin.roleAdmin")}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </ListItem>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
