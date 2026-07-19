import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { ProfileView } from "@/components/profile/profile-view";
import { getServerI18n } from "@/i18n/server";
import { getPublicProfile } from "@/lib/users.api";

type PageProps = {
  params: Promise<{ username: string }>;
  searchParams: Promise<{ year?: string }>;
};

/** Parse the `?year=` filter, ignoring anything that isn't a sane year. */
function parseYear(raw: string | undefined): number | undefined {
  const year = Number(raw);
  return Number.isInteger(year) && year >= 2000 && year <= 2200
    ? year
    : undefined;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { username } = await params;
  const profile = await getPublicProfile(username);
  if (!profile) {
    return { title: "PrintForHelp" };
  }
  const name = profile.user.full_name?.trim() || profile.user.username;
  return { title: `${name} (@${profile.user.username}) · PrintForHelp` };
}

/**
 * Public user profile at `/{username}`. A top-level dynamic route: static app
 * segments (login, parts, requests, …) win, and those names are reserved
 * handles server-side, so a username can never shadow a real page. Unknown or
 * private handles 404.
 */
export default async function UserProfilePage({
  params,
  searchParams,
}: PageProps) {
  const { username } = await params;
  const profile = await getPublicProfile(
    username,
    parseYear((await searchParams).year),
  );
  if (!profile) {
    notFound();
  }
  const [me, { dict, locale }] = await Promise.all([
    getCurrentUser(),
    getServerI18n(),
  ]);
  const isOwner =
    me?.username.toLowerCase() === profile.user.username.toLowerCase();

  return (
    <ProfileView
      profile={profile}
      isOwner={isOwner}
      dict={dict}
      locale={locale}
    />
  );
}
