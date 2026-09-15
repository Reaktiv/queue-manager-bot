import { api } from "../api/client";
import { DataList, ListRow } from "./DataList";
import { StarRating } from "./Icon";
import { Avatar, Badge, Empty, ErrorState, Sheet } from "./ui";
import { ListSkeleton } from "./Skeletons";
import { useAsyncData } from "../hooks/useAsyncData";
import { formatStamp } from "../lib/format";
import type { SuperAdminUserProfile } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  userId: number | null;
}

/**
 * Super Admin panelidagi "Userlar" ro'yxatida biror foydalanuvchiga
 * bosilganda ko'rsatiladigan profil.
 *
 * `ProfileSheet`dan farqi: bu yerda foydalanuvchi bitta guruhga emas,
 * global (bot darajasida) qaraladi - shuning uchun BIR EMAS, u a'zo
 * bo'lgan HAR BIR guruh o'z reytingi bilan alohida ko'rsatiladi (bitta
 * odam turli guruhda turlicha baholangan bo'lishi mumkin).
 */
export function SuperAdminUserProfileSheet({ open, onClose, userId }: Props) {
  const profile = useAsyncData<SuperAdminUserProfile>(
    "superadmin-user-profile",
    userId ? () => api.getSuperAdminUserProfile(userId) : null,
    [userId]
  );

  return (
    <Sheet open={open} onClose={onClose} title="Foydalanuvchi profili">
      {profile.loading ? (
        <ListSkeleton rows={3} />
      ) : profile.error ? (
        <ErrorState message={profile.error} onRetry={profile.reload} />
      ) : (
        profile.data && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Avatar name={profile.data.full_name} size="lg" crown={profile.data.is_super_admin} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-title-2 text-ink">{profile.data.full_name}</p>
                <p className="mt-0.5 truncate text-caption text-muted">
                  {profile.data.username ? `@${profile.data.username}` : "username yo'q"}
                  <span className="text-muted/70"> · </span>
                  <span className="tnum">{profile.data.telegram_id}</span>
                </p>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <Badge tone={profile.data.is_active ? "success" : "danger"}>
                    {profile.data.is_active ? "Faol" : "Blok"}
                  </Badge>
                  {profile.data.is_super_admin && <Badge tone="warning">Super Admin</Badge>}
                </div>
              </div>
            </div>

            <div className="space-y-2 rounded-card bg-surface-2 p-3.5">
              <div className="flex items-center justify-between gap-3">
                <span className="text-caption text-muted">Telefon</span>
                <span className="tnum text-caption font-semibold text-ink">
                  {profile.data.phone_number ?? "ulashilmagan"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-caption text-muted">Ro'yxatdan o'tgan</span>
                <span className="tnum text-caption font-semibold text-ink">
                  {formatStamp(profile.data.joined_at)}
                </span>
              </div>
            </div>

            <div>
              <p className="mb-2 px-1 text-micro uppercase text-muted">
                Guruhlar{profile.data.groups.length > 0 && ` · ${profile.data.groups.length}`}
              </p>
              {profile.data.groups.length === 0 ? (
                <Empty iconName="groups" title="Guruhi yo'q" hint="Bu foydalanuvchi hech qaysi guruhga a'zo emas." />
              ) : (
                <DataList>
                  {profile.data.groups.map((g, i) => (
                    <ListRow
                      key={g.group_id}
                      index={i}
                      title={g.group_name}
                      subtitle={g.role === "admin" ? "Admin" : "A'zo"}
                      trailing={
                        g.rating_stars !== null ? (
                          <div className="flex items-center gap-1">
                            <StarRating value={g.rating_stars} size={14} />
                            <span className="tnum text-caption text-muted">
                              {g.rating_stars.toFixed(1)}
                            </span>
                          </div>
                        ) : undefined
                      }
                    />
                  ))}
                </DataList>
              )}
            </div>
          </div>
        )
      )}
    </Sheet>
  );
}
