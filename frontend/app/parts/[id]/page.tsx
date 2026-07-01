import type { Metadata } from "next";
import { Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { EntityFeed } from "@/components/comments/entity-feed";
import { Markdown } from "@/components/comments/markdown";
import { EntityNoticeBanner } from "@/components/notices/entity-notice-banner";
import { RequestNotice } from "@/components/notices/request-notice";
import { getServerI18n } from "@/i18n/server";
import { listActivity, listComments } from "@/lib/feed.api";
import { getPart, getPartStats } from "@/lib/parts.api";
import { sourceProvider } from "@/lib/source-link";

import { RequestClaimBar } from "@/components/parts/request-claim-bar";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.parts.title} · PrintForHelp` };
}

export default async function PartDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ from?: string }>;
}) {
  const { id } = await params;
  const { from } = await searchParams;
  const part = await getPart(id);
  if (!part) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const t = dict.partDetail;
  // When the visitor arrived from My Contributions, send them back there
  // instead of the public catalog (`?from=contributions`).
  const fromContributions = from === "contributions";
  const backHref = fromContributions ? "/my-contributions" : "/parts";
  const backLabel = fromContributions ? t.backToContributions : t.back;
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canEdit = !!user && (user.id === part.owner_user_id || isMaintainer);

  const viewer = user ? { id: user.id, role: user.role } : null;
  const [comments, activity, stats] = await Promise.all([
    listComments("resource", part.id),
    listActivity("resource", part.id),
    getPartStats(part.id),
  ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href={backHref} className="text-sm text-muted hover:underline">
        {backLabel}
      </Link>

      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{part.name}</h1>
          {part.status === "discontinued" && (
            <Chip color="warning" variant="soft" size="sm">
              {t.discontinued}
            </Chip>
          )}
        </div>
        {canEdit && (
          <Link
            href={`/parts/${part.id}/edit`}
            className={buttonVariants({ size: "sm", variant: "secondary" })}
          >
            {t.edit}
          </Link>
        )}
      </div>

      <EntityNoticeBanner targetType="resource" targetId={part.id} />
      {canEdit && (
        <RequestNotice
          targetType="resource"
          targetId={part.id}
          revalidate={`/parts/${part.id}`}
          isMaintainer={isMaintainer}
        />
      )}

      {part.image_url && (
        // External, user-supplied image URL — see parts-catalog.tsx.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={part.image_url}
          alt={part.name}
          className="mt-6 max-h-96 w-full rounded-2xl object-cover"
        />
      )}

      {part.tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1">
          {part.tags.map((tag) => (
            <Chip key={tag} variant="soft" size="sm">
              {tag}
            </Chip>
          ))}
        </div>
      )}

      {part.source_url && (
        <div className="mt-6">
          <a
            href={part.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonVariants({ size: "sm" })}
          >
            {t.sourceLinks[sourceProvider(part.source_url)]}
            <span aria-hidden="true"> ↗</span>
          </a>
        </div>
      )}

      {part.description && (
        <div className="mt-8">
          <h2 className="mb-2 text-lg font-semibold">{t.descriptionHeading}</h2>
          <Markdown source={part.description} />
        </div>
      )}

      <div className="mt-10">
        <RequestClaimBar stats={stats} labels={dict.partStats} />
      </div>

      <section
        className="mt-8 rounded-2xl border p-5"
        style={{ background: "var(--card)", borderColor: "var(--card-border)" }}
      >
        <h2 className="text-lg font-semibold">{t.involvedHeading}</h2>
        <p className="mt-1 text-sm text-muted">{t.involvedSubtitle}</p>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col rounded-xl border border-[color:var(--card-border)] p-4">
            <h3 className="font-semibold">{t.requestCta}</h3>
            <p className="mt-1 flex-1 text-sm text-muted">{t.requestCtaHint}</p>
            <Link
              href="/requests/new"
              className={`${buttonVariants({ size: "sm" })} mt-3 self-start`}
            >
              {t.requestCta}
            </Link>
          </div>
          <div className="flex flex-col rounded-xl border border-[color:var(--card-border)] p-4">
            <h3 className="font-semibold">{t.claimCta}</h3>
            <p className="mt-1 flex-1 text-sm text-muted">{t.claimCtaHint}</p>
            <Link
              href="/requests"
              className={`${buttonVariants({ size: "sm", variant: "secondary" })} mt-3 self-start`}
            >
              {t.claimCta}
            </Link>
          </div>
        </div>

        <ol className="mt-6 flex flex-col gap-3 sm:flex-row sm:gap-4">
          {[t.howStep1, t.howStep2, t.howStep3].map((step, i) => (
            <li
              key={i}
              className="flex flex-1 items-start gap-3 rounded-xl border border-[color:var(--card-border)] p-3 text-sm"
            >
              <span
                aria-hidden
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                style={{ background: "var(--accent-strong)" }}
              >
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/parts/${part.id}`}
          entityType="resource"
          entityId={part.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
