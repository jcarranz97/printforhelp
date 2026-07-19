import type { Metadata } from "next";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { cookies } from "next/headers";

import { getCurrentUser } from "@/actions/auth.action";
import { ArchivedCenters } from "@/components/centers/archived-centers";
import { CentersDirectory } from "@/components/centers/centers-directory";
import { UnverifiedCenters } from "@/components/centers/unverified-centers";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listCollectionCenters } from "@/lib/collection-centers.api";

import CentersMap from "@/components/centers/centers-map-loader";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return {
    title: `${dict.centers.title} · PrintForHelp`,
    description: dict.centers.subtitle,
  };
}

export default async function CentersPage() {
  const user = await getCurrentUser();
  const token = user
    ? (await cookies()).get(AUTH_COOKIE_NAME)?.value
    : undefined;
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const { dict } = await getServerI18n();

  // The public directory includes unverified centers (badged "No
  // verificado"). Maintainers additionally get a focused review queue of
  // the unverified ones with one-click verification.
  const centers = await listCollectionCenters();
  const [unverified, archived] =
    isMaintainer && token
      ? await Promise.all([
          listCollectionCenters({ verified: false }, token),
          listCollectionCenters({ active: false }, token),
        ])
      : [[], []];

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{dict.centers.title}</h1>
          <p className="mt-1 text-sm text-muted">{dict.centers.subtitle}</p>
        </div>
        <Link href="/centers/new" className={buttonVariants({ size: "sm" })}>
          {dict.centers.register}
        </Link>
      </div>

      <CentersMap centers={centers} />
      <CentersDirectory centers={centers} />

      {isMaintainer && unverified.length > 0 && (
        <UnverifiedCenters centers={unverified} />
      )}

      {isMaintainer && archived.length > 0 && (
        <ArchivedCenters centers={archived} />
      )}
    </main>
  );
}
