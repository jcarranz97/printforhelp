import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { ArchiveResourceButton } from "@/components/resources/archive-resource-button";
import { EditSupplyForm } from "@/components/supplies/edit-supply-form";
import { getServerI18n } from "@/i18n/server";
import { getSupply, listSupplies } from "@/lib/supplies.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.supplyEdit.title} · PrintForHelp` };
}

export default async function EditSupplyPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await getCurrentUser();
  if (!user) {
    redirect(`/login?next=/supplies/${id}/edit`);
  }

  const supply = await getSupply(id);
  if (!supply) {
    notFound();
  }

  // UX guard only — the backend re-checks effective-owner rights.
  const isMaintainer = user.role === "maintainer" || user.role === "admin";
  if (user.id !== supply.owner_user_id && !isMaintainer) {
    redirect(`/supplies/${id}`);
  }

  const { dict } = await getServerI18n();
  const t = dict.supplyEdit;
  const supplies = await listSupplies();
  const tagSuggestions = Array.from(new Set(supplies.flatMap((s) => s.tags)));
  const unitSuggestions = Array.from(new Set(supplies.flatMap((s) => s.units)));

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href={`/supplies/${id}`}
        className="text-sm text-muted hover:underline"
      >
        {t.back}
      </Link>
      <h1 className="mt-4 mb-1 text-2xl font-bold">{t.title}</h1>
      <p className="mb-8 text-sm text-muted">{t.subtitle}</p>
      <EditSupplyForm
        supply={supply}
        suggestions={tagSuggestions}
        unitSuggestions={unitSuggestions}
      />
      <div
        className="mt-8 border-t pt-6"
        style={{ borderColor: "var(--card-border)" }}
      >
        <ArchiveResourceButton resourceId={supply.id} kind="supply" />
      </div>
    </main>
  );
}
