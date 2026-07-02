import type { Metadata } from "next";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { getCurrentUser } from "@/actions/auth.action";
import { SuppliesCatalog } from "@/components/supplies/supplies-catalog";
import { getServerI18n } from "@/i18n/server";
import { listSupplies } from "@/lib/supplies.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return {
    title: `${dict.supplies.title} · PrintForHelp`,
    description: dict.supplies.subtitle,
  };
}

export default async function SuppliesPage() {
  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const supplies = await listSupplies();

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{dict.supplies.title}</h1>
          <p className="mt-1 text-sm text-muted">{dict.supplies.subtitle}</p>
        </div>
        {user && (
          <Link href="/supplies/new" className={buttonVariants({ size: "sm" })}>
            {dict.supplies.register}
          </Link>
        )}
      </div>

      <SuppliesCatalog supplies={supplies} />
    </main>
  );
}
