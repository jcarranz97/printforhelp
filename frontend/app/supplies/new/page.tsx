import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { CreateSupplyForm } from "@/components/supplies/create-supply-form";
import { getServerI18n } from "@/i18n/server";
import { listSupplies } from "@/lib/supplies.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.supplyNew.title} · PrintForHelp` };
}

export default async function NewSupplyPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/supplies/new");
  }
  const { dict } = await getServerI18n();
  const t = dict.supplyNew;
  const supplies = await listSupplies();
  const tagSuggestions = Array.from(new Set(supplies.flatMap((s) => s.tags)));
  const unitSuggestions = Array.from(new Set(supplies.flatMap((s) => s.units)));

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/supplies" className="text-sm text-muted hover:underline">
        {t.back}
      </Link>
      <h1 className="mt-4 mb-1 text-2xl font-bold">{t.title}</h1>
      <p className="mb-8 text-sm text-muted">{t.subtitle}</p>
      <CreateSupplyForm
        suggestions={tagSuggestions}
        unitSuggestions={unitSuggestions}
      />
    </main>
  );
}
