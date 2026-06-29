import type { Metadata } from "next";
import { Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { Markdown } from "@/components/comments/markdown";
import { getServerI18n } from "@/i18n/server";
import { getPart } from "@/lib/parts.api";
import { sourceProvider } from "@/lib/source-link";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.parts.title} · PrintForHelp` };
}

export default async function PartDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const part = await getPart(id);
  if (!part) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const t = dict.partDetail;
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canEdit = !!user && (user.id === part.owner_user_id || isMaintainer);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/parts" className="text-sm text-muted hover:underline">
        {t.back}
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
    </main>
  );
}
