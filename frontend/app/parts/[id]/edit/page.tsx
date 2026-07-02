import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { EditPartForm } from "@/components/parts/edit-part-form";
import { ArchiveResourceButton } from "@/components/resources/archive-resource-button";
import { getServerI18n } from "@/i18n/server";
import { getPart, listParts } from "@/lib/parts.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.partEdit.title} · PrintForHelp` };
}

export default async function EditPartPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await getCurrentUser();
  if (!user) {
    redirect(`/login?next=/parts/${id}/edit`);
  }

  const part = await getPart(id);
  if (!part) {
    notFound();
  }

  // UX guard only — the backend re-checks effective-owner rights.
  const isMaintainer = user.role === "maintainer" || user.role === "admin";
  if (user.id !== part.owner_user_id && !isMaintainer) {
    redirect(`/parts/${id}`);
  }

  const { dict } = await getServerI18n();
  const t = dict.partEdit;
  const parts = await listParts();
  const tagSuggestions = Array.from(new Set(parts.flatMap((p) => p.tags)));

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href={`/parts/${id}`}
        className="text-sm text-muted hover:underline"
      >
        {t.back}
      </Link>
      <h1 className="mt-4 mb-1 text-2xl font-bold">{t.title}</h1>
      <p className="mb-8 text-sm text-muted">{t.subtitle}</p>
      <EditPartForm part={part} suggestions={tagSuggestions} />
      <div
        className="mt-8 border-t pt-6"
        style={{ borderColor: "var(--card-border)" }}
      >
        <ArchiveResourceButton resourceId={part.id} kind="part" />
      </div>
    </main>
  );
}
