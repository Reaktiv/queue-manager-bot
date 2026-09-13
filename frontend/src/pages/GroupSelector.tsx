import { AppHeader, AppMain } from "../components/AppScreen";
import { DataList, ListRow } from "../components/DataList";
import { Icon } from "../components/Icon";
import { Avatar, Badge, Empty, ErrorState } from "../components/ui";
import { ListSkeleton } from "../components/Skeletons";
import type { AuthUser, GroupSummary } from "../types";

interface Props {
  user: AuthUser;
  groups: GroupSummary[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelect: (group: GroupSummary) => void;
  onOpenSuperAdmin?: () => void;
}

/**
 * Kirish ekrani: salomlashuv + guruhlar ro'yxati.
 *
 * Ilgari bu yerda uch bosqichli gradient sarlavha va ikkita dekorativ
 * blur doira bor edi - ular ekranning ~30% ini egallab, hech qanday
 * ma'lumot bermasdi. Endi sarlavha oddiy glass xrom, ro'yxat esa
 * yagona yuza.
 */
export function GroupSelector({
  user,
  groups,
  loading,
  error,
  onRetry,
  onSelect,
  onOpenSuperAdmin,
}: Props) {
  const firstName = user.full_name.split(/\s+/)[0];
  const hour = new Date().getHours();
  const greet =
    hour < 5 ? "Xayrli tun" : hour < 12 ? "Xayrli tong" : hour < 18 ? "Xayrli kun" : "Xayrli kech";

  return (
    <>
      <AppHeader>
        <div className="pt-1">
          <p className="text-micro uppercase text-muted">{greet}</p>
          <h1 className="mt-0.5 truncate text-title-1 text-ink">{firstName}</h1>
        </div>
      </AppHeader>

      <AppMain>
        <div className="space-y-4">
          {onOpenSuperAdmin && (
            <DataList>
              <ListRow
                leading={
                  <span className="grid h-10 w-10 place-items-center rounded-control bg-warning/18 text-warning">
                    <Icon name="crown" size={20} />
                  </span>
                }
                title="Super Admin panel"
                subtitle="Tizim statistikasi va boshqaruv"
                onClick={onOpenSuperAdmin}
              />
            </DataList>
          )}

          <section>
            <p className="mb-2 px-1 text-micro uppercase text-muted">
              Guruhlaringiz
              {groups && groups.length > 0 && ` · ${groups.length}`}
            </p>

            {loading ? (
              <ListSkeleton rows={3} />
            ) : error ? (
              <ErrorState message={error} onRetry={onRetry} />
            ) : !groups || groups.length === 0 ? (
              <Empty
                iconName="compass"
                title="Guruh topilmadi"
                hint="Botga qayting va /join buyrug'i bilan mavjud guruhga qo'shiling yoki /creategroup bilan yangisini oching."
              />
            ) : (
              <DataList>
                {groups.map((group, i) => (
                  <ListRow
                    key={group.id}
                    index={i}
                    leading={<Avatar name={group.name} crown={group.role === "admin"} />}
                    title={group.name}
                    subtitle={group.timezone}
                    trailing={
                      <Badge tone={group.role === "admin" ? "warning" : "neutral"}>
                        {group.role === "admin" ? "Admin" : "A'zo"}
                      </Badge>
                    }
                    onClick={() => onSelect(group)}
                    ariaLabel={`${group.name} guruhini ochish`}
                  />
                ))}
              </DataList>
            )}
          </section>
        </div>
      </AppMain>
    </>
  );
}
