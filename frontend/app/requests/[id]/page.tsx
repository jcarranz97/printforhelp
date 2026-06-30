import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { EntityFeed } from "@/components/comments/entity-feed";
import { RequestDetailView } from "@/components/requests/request-detail";
import { getServerI18n } from "@/i18n/server";
import { listCollectionCenters } from "@/lib/collection-centers.api";
import { listActivity, listComments } from "@/lib/feed.api";
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
  const [parts, centers, comments, activity] = await Promise.all([
    listParts(),
    listCollectionCenters({ verified: true }),
    listComments("request", request.id),
    listActivity("request", request.id),
  ]);

  const partNames: Record<string, string> = Object.fromEntries(
    parts.map((part) => [part.id, part.name]),
  );
  // Only active, non-discontinued parts can be added as new items.
  const activeParts = parts.filter(
    (part) => part.active && part.status === "active",
  );
  const centerOptions = centers
    .filter((center) => center.status === "active")
    .map((center) => ({ id: center.id, name: center.name }));

  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canManage =
    !!user && (user.id === request.requester_user_id || isMaintainer);
  const viewer = user ? { id: user.id, role: user.role } : null;
  const t = dict.requestDetail;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/requests" className="text-sm text-muted hover:underline">
        {t.back}
      </Link>
      <div className="mt-6">
        <RequestDetailView
          request={request}
          parts={activeParts}
          partNames={partNames}
          centers={centerOptions}
          isLoggedIn={!!user}
          canManage={canManage}
        />
      </div>

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/requests/${request.id}`}
          entityType="request"
          entityId={request.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
