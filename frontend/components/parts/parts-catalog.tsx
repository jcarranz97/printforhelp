"use client";

import { Card, Chip, Input } from "@heroui/react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useI18n } from "@/i18n/provider";
import { markdownToExcerpt } from "@/lib/markdown-excerpt";
import type { Part } from "@/lib/parts.api";

/**
 * Public Part catalog: a name search over a responsive grid of cards.
 * Each card shows the design's image (when present), tags, status, and a
 * link to download the source file.
 */
export function PartsCatalog({ parts }: { parts: Part[] }) {
  const { dict } = useI18n();
  const t = dict.parts;
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return parts;
    }
    return parts.filter((p) => p.name.toLowerCase().includes(q));
  }, [parts, query]);

  return (
    <div className="flex flex-col gap-6">
      <div className="w-full sm:w-72">
        <Input
          aria-label={t.search}
          placeholder={t.searchPlaceholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      {filtered.length === 0 ? (
        <Card variant="transparent" className="py-12 text-center">
          <Card.Content>
            <p className="text-muted">{t.empty}</p>
          </Card.Content>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((part) => (
            <PartCard key={part.id} part={part} />
          ))}
        </div>
      )}
    </div>
  );
}

function PartCard({ part }: { part: Part }) {
  const { dict } = useI18n();
  const t = dict.parts;
  return (
    <Link
      href={`/parts/${part.id}`}
      className="rounded-2xl transition-shadow hover:shadow-md"
      aria-label={`${t.viewDetails} ${part.name}`}
    >
      <Card className="h-full">
        {part.image_url && (
          // External, user-supplied image URL: next/image would need every
          // host allow-listed, so a plain img is the pragmatic choice here.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={part.image_url}
            alt={part.name}
            className="h-40 w-full rounded-t-2xl object-cover"
          />
        )}
        <Card.Header>
          <Card.Title>{part.name}</Card.Title>
          {part.description && (
            <Card.Description className="line-clamp-2">
              {markdownToExcerpt(part.description)}
            </Card.Description>
          )}
        </Card.Header>
        <Card.Content className="flex flex-col gap-2 text-sm">
          {part.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {part.tags.map((tag) => (
                <Chip key={tag} variant="soft" size="sm">
                  {tag}
                </Chip>
              ))}
            </div>
          )}
        </Card.Content>
        <Card.Footer>
          {part.status === "discontinued" && (
            <Chip color="warning" variant="soft" size="sm">
              {t.discontinued}
            </Chip>
          )}
        </Card.Footer>
      </Card>
    </Link>
  );
}
