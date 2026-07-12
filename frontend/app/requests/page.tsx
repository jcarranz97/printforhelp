import type { Metadata } from "next";
import { buttonVariants } from "@heroui/styles";
import { cookies } from "next/headers";
import Link from "next/link";

import { getCurrentUser } from "@/actions/auth.action";
import { RequestsList } from "@/components/requests/requests-list";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listRequests } from "@/lib/requests.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return {
    title: `${dict.requests.title} · PrintForHelp`,
    description: dict.requests.subtitle,
  };
}

export default async function RequestsPage() {
  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  // Passing the token folds in the campaigns this viewer is entitled to see
  // but the public is not — their own drafts, and (for maintainers) everyone's.
  const cookieStore = await cookies();
  const requests = await listRequests(
    undefined,
    cookieStore.get(AUTH_COOKIE_NAME)?.value,
  );

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{dict.requests.title}</h1>
          <p className="mt-1 text-sm text-muted">{dict.requests.subtitle}</p>
        </div>
        {user && (
          <Link href="/requests/new" className={buttonVariants({ size: "sm" })}>
            {dict.requests.register}
          </Link>
        )}
      </div>

      <RequestsList requests={requests} />
    </main>
  );
}
