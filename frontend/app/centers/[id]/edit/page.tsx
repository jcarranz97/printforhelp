import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { EditCenterForm } from "@/components/centers/edit-center-form";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import {
  canManageCenter,
  getCollectionCenter,
} from "@/lib/collection-centers.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.centerEdit.title} · PrintForHelp` };
}

export default async function EditCenterPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await getCurrentUser();
  if (!user) {
    redirect(`/login?next=/centers/${id}/edit`);
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;

  const center = await getCollectionCenter(id, token);
  if (!center) {
    notFound();
  }

  // UX guard only — the action re-checks authorization server-side too.
  const canManage = await canManageCenter(center.id, token);
  if (!canManage) {
    redirect(`/centers/${center.id}`);
  }

  const { dict } = await getServerI18n();
  const t = dict.centerEdit;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href={`/centers/${center.id}`}
        className="text-sm text-muted hover:text-foreground"
      >
        {t.back}
      </Link>

      <div className="mt-4 mb-8">
        <h1 className="text-2xl font-bold">{t.title}</h1>
        <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
      </div>

      <EditCenterForm center={center} />
    </main>
  );
}
