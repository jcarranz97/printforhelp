import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";

import {
  type CenterFormValues,
  CreateCenterForm,
} from "@/components/centers/create-center-form";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { getCollectionCenter } from "@/lib/collection-centers.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.centerNew.title} · PrintForHelp` };
}

export default async function NewCenterPage({
  searchParams,
}: {
  searchParams: Promise<{ cloneFrom?: string }>;
}) {
  const { cloneFrom } = await searchParams;
  const { dict } = await getServerI18n();
  const t = dict.centerNew;

  // When cloning, pre-fill the form from an existing center. The token is
  // forwarded so private (unverified/inactive) centers the caller can see
  // are also clonable; a missing/unreadable source just yields a blank form.
  let initialValues: CenterFormValues | undefined;
  if (cloneFrom) {
    const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
    const source = await getCollectionCenter(cloneFrom, token);
    if (source) {
      initialValues = {
        name: source.name,
        country: source.country,
        city: source.city,
        address: source.address,
        location_url: source.location_url ?? undefined,
        contact: source.contact,
        opening_hours: source.opening_hours ?? undefined,
        description: source.description ?? undefined,
      };
    }
  }

  const cloning = initialValues !== undefined;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href="/centers"
        className="text-sm text-muted hover:text-foreground"
      >
        {t.back}
      </Link>

      <div className="mt-4 mb-8">
        <h1 className="text-2xl font-bold">
          {cloning ? t.cloneTitle : t.title}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {cloning ? t.cloneSubtitle : t.subtitle}
        </p>
      </div>

      <CreateCenterForm initialValues={initialValues} />
    </main>
  );
}
