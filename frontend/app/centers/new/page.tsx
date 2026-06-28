import type { Metadata } from "next";
import Link from "next/link";

import { CreateCenterForm } from "@/components/centers/create-center-form";
import { getServerI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.centerNew.title} · PrintForHelp` };
}

export default async function NewCenterPage() {
  const { dict } = await getServerI18n();
  const t = dict.centerNew;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href="/centers"
        className="text-sm text-muted hover:text-foreground"
      >
        {t.back}
      </Link>

      <div className="mt-4 mb-8">
        <h1 className="text-2xl font-bold">{t.title}</h1>
        <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
      </div>

      <CreateCenterForm />
    </main>
  );
}
