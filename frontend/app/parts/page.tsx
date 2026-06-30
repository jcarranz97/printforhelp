import type { Metadata } from "next";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { getCurrentUser } from "@/actions/auth.action";
import { PartsCatalog } from "@/components/parts/parts-catalog";
import { getServerI18n } from "@/i18n/server";
import { listParts, listPartStatsMap } from "@/lib/parts.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return {
    title: `${dict.parts.title} · PrintForHelp`,
    description: dict.parts.subtitle,
  };
}

export default async function PartsPage() {
  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const [parts, statsById] = await Promise.all([
    listParts(),
    listPartStatsMap(),
  ]);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{dict.parts.title}</h1>
          <p className="mt-1 text-sm text-muted">{dict.parts.subtitle}</p>
        </div>
        {user && (
          <Link href="/parts/new" className={buttonVariants({ size: "sm" })}>
            {dict.parts.register}
          </Link>
        )}
      </div>

      <PartsCatalog parts={parts} statsById={statsById} />
    </main>
  );
}
