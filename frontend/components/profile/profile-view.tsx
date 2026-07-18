import { Card, Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { UserAvatar } from "@/components/common/user-avatar";
import type { Dictionary } from "@/i18n/dictionaries/es";
import type { ProfileProject, PublicProfile } from "@/lib/users.api";

type ProfileViewProps = {
  profile: PublicProfile;
  isOwner: boolean;
  dict: Dictionary;
  locale: string;
};

/** Map a contribution status to a HeroUI Chip color. */
const STATUS_COLOR: Record<
  ProfileProject["status"],
  "default" | "accent" | "success" | "danger"
> = {
  claimed: "default",
  prepared: "accent",
  delivered: "success",
  received: "success",
  released: "danger",
};

function formatDate(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

/**
 * The public user profile: a left identity column (avatar, name, handle, bio,
 * "Edit profile" for the owner) and a right column listing the projects the
 * user collaborates on, GitHub-style.
 */
export function ProfileView({
  profile,
  isOwner,
  dict,
  locale,
}: ProfileViewProps) {
  const t = dict.profile;
  const { user, projects, projects_count } = profile;
  const displayName = user.full_name?.trim() || user.username;

  const heading = [
    t.projectsHeadingBefore,
    user.username,
    t.projectsHeadingAfter,
  ]
    .filter((part) => part.length > 0)
    .join(" ");

  return (
    <main className="mx-auto grid max-w-5xl gap-8 px-4 py-8 md:grid-cols-[280px_1fr] md:items-start">
      <aside className="flex flex-col gap-4">
        <UserAvatar
          username={user.username}
          fullName={user.full_name}
          avatarUrl={user.avatar_url}
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
          {t.memberSince} {formatDate(user.created_at, locale)}
        </p>
      </aside>

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline gap-2">
          <h2 className="text-lg font-bold">{heading}</h2>
          <Chip size="sm" variant="secondary">
            {projects_count}
          </Chip>
        </div>

        {projects.length === 0 ? (
          <Card variant="transparent" className="py-12 text-center">
            <Card.Content>
              <p className="text-sm text-muted">{t.emptyProjects}</p>
            </Card.Content>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {projects.map((project, index) => (
              <ProjectCard
                key={`${project.request_id}-${project.item_number}-${index}`}
                project={project}
                dict={dict}
                locale={locale}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function ProjectCard({
  project,
  dict,
  locale,
}: {
  project: ProfileProject;
  dict: Dictionary;
  locale: string;
}) {
  const t = dict.profile;
  const unitLabel = project.unit?.trim() || t.unitsPieces;

  return (
    <Card className="h-full">
      <Card.Content className="flex flex-col gap-3 p-4">
        <div className="flex items-start gap-3">
          {project.resource_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={project.resource_image_url}
              alt=""
              className="size-12 shrink-0 rounded-lg border border-border object-cover"
            />
          ) : (
            <div className="size-12 shrink-0 rounded-lg border border-border bg-default-100" />
          )}
          <div className="flex min-w-0 flex-col">
            <Link
              href={`/requests/${project.request_id}/items/${project.item_number}`}
              className="truncate font-semibold text-accent hover:underline"
            >
              {project.resource_name}
            </Link>
            <span className="truncate text-xs text-muted">
              {t.requestPrefix} · {project.request_title}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Chip size="sm" variant="soft" color={STATUS_COLOR[project.status]}>
            {t.status[project.status]}
          </Chip>
          <span className="text-xs text-muted">
            {project.quantity} {unitLabel}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          {project.collection_center_country ? (
            <span>{project.collection_center_country}</span>
          ) : null}
          <span>{formatDate(project.last_activity_at, locale)}</span>
        </div>
      </Card.Content>
    </Card>
  );
}
