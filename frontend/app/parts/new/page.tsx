import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { CreatePartForm } from "@/components/parts/create-part-form";
import { getServerI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.partNew.title} · PrintForHelp` };
}

export default async function NewPartPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/parts/new");
  }
  const { dict } = await getServerI18n();
  const t = dict.partNew;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/parts" className="text-sm text-muted hover:underline">
        {t.back}
      </Link>
      <h1 className="mt-4 mb-1 text-2xl font-bold">{t.title}</h1>
      <p className="mb-8 text-sm text-muted">{t.subtitle}</p>
      <CreatePartForm />
    </main>
  );
}
