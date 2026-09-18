import { api } from "../api/client";
import {
  Avatar,
  Badge,
  ErrorState,
  LabelValueRow,
  Ring,
  Sheet,
  Surface,
} from "./ui";
import { ListSkeleton } from "./Skeletons";
import { useAsyncData } from "../hooks/useAsyncData";
import type { MemberStatistics } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  memberId: number | null;
  fullName: string;
  role: "admin" | "member";
}

/**
 * A'zo profili: bajarish statistikasi.
 *
 * Ham a'zoning o'zi (MemberDashboard - o'z profilini ko'rish uchun),
 * ham admin (AdminDashboard - boshqa a'zoning profilini ko'rish uchun)
 * ishlatadi - shuning uchun ism/rol tashqaridan (allaqachon ma'lum,
 * qayta so'rov shart emas) beriladi, faqat statistika o'zi so'raladi.
 */
export function ProfileSheet({ open, onClose, memberId, fullName, role }: Props) {
  const stats = useAsyncData<MemberStatistics>(
    "member-stats",
    memberId ? () => api.getMemberStatistics(memberId) : null,
    [memberId]
  );

  return (
    <Sheet open={open} onClose={onClose} title="Profil">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Avatar name={fullName} size="lg" crown={role === "admin"} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-title-2 text-ink">{fullName}</p>
            <div className="mt-1">
              <Badge tone={role === "admin" ? "warning" : "neutral"}>
                {role === "admin" ? "Admin" : "A'zo"}
              </Badge>
            </div>
          </div>
        </div>

        {stats.loading ? (
          <ListSkeleton rows={2} />
        ) : stats.error ? (
          <ErrorState message={stats.error} onRetry={stats.reload} />
        ) : (
          stats.data && (
            <Surface className="flex items-center gap-4">
              <Ring value={stats.data.completion_rate} label="bajarildi" />
              <div className="grid min-w-0 flex-1 gap-2.5">
                <LabelValueRow
                  label="Bajarilgan"
                  value={`${stats.data.completed} / ${stats.data.total}`}
                />
              </div>
            </Surface>
          )
        )}
      </div>
    </Sheet>
  );
}
