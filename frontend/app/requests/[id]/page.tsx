import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { RequestDetailView } from "@/components/requests/request-detail";
import { getServerI18n } from "@/i18n/server";
import { listCollectionCenters } from "@/lib/collection-centers.api";
import { listParts } from "@/lib/parts.api";
import { getRequest } from "@/lib/requests.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.requests.title} · PrintForHelp` };
}

export default async function RequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const request = await getRequest(id);
  if (!request) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const [parts, centers] = await Promise.all([
    listParts(),
    listCollectionCenters({ verified: true }),
  ]);

  const partNames: Record<string, string> = Object.fromEntries(
    parts.map((part) => [part.id, part.name]),
  );
  const centerOptions = centers
    .filter((center) => center.status === "active")
    .map((center) => ({ id: center.id, name: center.name }));

  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canClose =
    !!user && (user.id === request.requester_user_id || isMaintainer);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/requests" className="text-sm text-muted hover:underline">
        {dict.requestDetail.back}
      </Link>
      <div className="mt-6">
        <RequestDetailView
          request={request}
          partNames={partNames}
          centers={centerOptions}
          isLoggedIn={!!user}
          canClose={canClose}
        />
      </div>
    </main>
  );
}
