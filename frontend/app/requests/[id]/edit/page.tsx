import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { cookies } from "next/headers";

import { getCurrentUser } from "@/actions/auth.action";
import { EditRequestForm } from "@/components/requests/edit-request-form";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { requestCenterOptions } from "@/lib/request-centers";
import { getRequest, listBeneficiarySuggestions } from "@/lib/requests.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.requestEdit.title} · PrintForHelp` };
}

export default async function EditRequestPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await getCurrentUser();
  if (!user) {
    redirect(`/login?next=/requests/${id}/edit`);
  }

  const request = await getRequest(id);
  if (!request) {
    notFound();
  }

  // UX guard only — the backend re-checks effective-requester rights.
  const isMaintainer = user.role === "maintainer" || user.role === "admin";
  if (user.id !== request.requester_user_id && !isMaintainer) {
    redirect(`/requests/${id}`);
  }

  const { dict } = await getServerI18n();
  const t = dict.requestEdit;
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value ?? "";
  const [centerOptions, beneficiarySuggestions] = await Promise.all([
    requestCenterOptions(token, request.preferred_collection_center_ids),
    listBeneficiarySuggestions(token),
  ]);

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href={`/requests/${id}`}
        className="text-sm text-muted hover:underline"
      >
        {t.back}
      </Link>
      <h1 className="mt-4 mb-1 text-2xl font-bold">{t.title}</h1>
      <p className="mb-8 text-sm text-muted">{t.subtitle}</p>
      <EditRequestForm
        request={request}
        centers={centerOptions}
        beneficiarySuggestions={beneficiarySuggestions}
      />
    </main>
  );
}
