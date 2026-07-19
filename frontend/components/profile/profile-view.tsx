import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { UserAvatar } from "@/components/common/user-avatar";
import { ActivityTimeline } from "@/components/profile/activity-timeline";
import { ContributionCalendar } from "@/components/profile/contribution-calendar";
import { YearSelector } from "@/components/profile/year-selector";
import type { Dictionary } from "@/i18n/dictionaries/es";
import type { PublicProfile } from "@/lib/users.api";

type ProfileViewProps = {
  profile: PublicProfile;
  isOwner: boolean;
  dict: Dictionary;
  locale: string;
};

/** Fill `{name}` placeholders in a dictionary string. */
function fill(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

function formatDay(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    month: "short",
    day: "numeric",
  }).format(date);
}

/**
 * The public user profile: a left identity column (avatar, name, handle, bio,
 * "Edit profile" for the owner) and a right column with a GitHub-style
 * contribution activity timeline, loaded a couple of months at a time.
 */
export function ProfileView({
  profile,
  isOwner,
  dict,
  locale,
}: ProfileViewProps) {
  const t = dict.profile;
  const { user, activity } = profile;
  const displayName = user.full_name?.trim() || user.username;

  return (
    <main className="mx-auto grid max-w-5xl gap-8 px-4 py-8 md:grid-cols-[280px_1fr] md:items-start">
      <aside className="flex flex-col gap-4">
        <UserAvatar
          username={user.username}
          fullName={user.full_name}
          avatarUrl={user.avatar_url}
          crop={{
            x: user.avatar_crop_x,
            y: user.avatar_crop_y,
            w: user.avatar_crop_w,
            h: user.avatar_crop_h,
          }}
          className="size-40 self-start md:size-56"
          fallbackClassName="text-5xl md:text-6xl"
        />
        <div className="flex flex-col">
          <h1 className="text-2xl font-bold leading-tight">{displayName}</h1>
          {user.full_name?.trim() ? (
            <span className="text-lg text-muted">{user.username}</span>
          ) : null}
        </div>
        {user.bio?.trim() ? (
          <p className="text-sm leading-relaxed text-foreground/80">
            {user.bio}
          </p>
        ) : null}
        {isOwner ? (
          <Link
            href="/settings/profile"
            className={buttonVariants({ variant: "secondary", size: "sm" })}
          >
            {t.editProfile}
          </Link>
        ) : null}
        <p className="text-xs text-muted">
          {t.memberSince} {formatDay(user.created_at, locale)}
        </p>
      </aside>

      <section className="flex min-w-0 flex-col gap-5">
        <h2 className="text-base text-foreground/80">
          <strong className="font-bold text-foreground">
            {profile.contributions_total.toLocaleString(locale)}
          </strong>{" "}
          {profile.selected_year === null
            ? t.contributionsLastYear
            : fill(t.contributionsInYear, { year: profile.selected_year })}
        </h2>

        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <div className="min-w-0 flex-1">
            <ContributionCalendar
              days={profile.contribution_days}
              year={profile.selected_year}
              dict={dict}
              locale={locale}
            />
          </div>
          <YearSelector
            username={user.username}
            years={profile.available_years}
            selected={profile.selected_year}
            dict={dict}
          />
        </div>

        <div className="flex flex-col">
          <h3 className="mb-3 text-sm text-foreground/80">{t.activityTitle}</h3>
          <ActivityTimeline
            // Remount on year change: the timeline accumulates pages in local
            // state, and without a new key React would keep the previous
            // year's months while the rest of the page switched.
            key={profile.selected_year ?? "all"}
            username={user.username}
            initialPage={activity}
            year={profile.selected_year}
          />
        </div>
      </section>
    </main>
  );
}
