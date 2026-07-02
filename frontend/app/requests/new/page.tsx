import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { CreateRequestForm } from "@/components/requests/create-request-form";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listParts } from "@/lib/parts.api";
import { requestCenterOptions } from "@/lib/request-centers";
import { toResourceOptions } from "@/lib/resource-options";
import { listSupplies } from "@/lib/supplies.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.requestNew.title} · PrintForHelp` };
}

export default async function NewRequestPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/requests/new");
  }
  const { dict } = await getServerI18n();
  const t = dict.requestNew;
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value ?? "";
  const [parts, supplies, centerOptions] = await Promise.all([
    listParts({ status: "active" }),
    listSupplies({ status: "active" }),
    requestCenterOptions(token),
  ]);
  const resources = toResourceOptions(parts, supplies);

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/requests" className="text-sm text-muted hover:underline">
        {t.back}
      </Link>
      <h1 className="mt-4 mb-1 text-2xl font-bold">{t.title}</h1>
      <p className="mb-8 text-sm text-muted">{t.subtitle}</p>
      <CreateRequestForm resources={resources} centers={centerOptions} />
    </main>
  );
}
