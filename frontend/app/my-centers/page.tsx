import { Card } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { CenterCard } from "@/components/centers/center-card";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listMyCollectionCenters } from "@/lib/collection-centers.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.myCenters.title} · PrintForHelp` };
}

/**
 * The centres the caller staffs — owned, contributed to, or via an owning org.
 *
 * The public `/centers` directory is for finding a drop-off; this is for
 * running one. It is also the only way to reach an **unlisted** centre, which
 * by design never appears in the directory at all.
 *
 * Laid out exactly like the directory — same card, same grid, same page
 * chrome — so it reads as another view of the same thing rather than a
 * different screen that happens to list centres.
 */
export default async function MyCentersPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.myCenters;
  const centers = token ? await listMyCollectionCenters(token) : [];

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t.title}</h1>
          <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
        </div>
        <Link href="/centers/new" className={buttonVariants({ size: "sm" })}>
          {dict.centers.register}
        </Link>
      </div>

      {centers.length === 0 ? (
        <Card variant="transparent" className="py-12 text-center">
          <Card.Content>
            <p className="text-muted">{t.empty}</p>
          </Card.Content>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {centers.map((center) => (
            <CenterCard key={center.id} center={center} />
          ))}
        </div>
      )}
    </main>
  );
}
