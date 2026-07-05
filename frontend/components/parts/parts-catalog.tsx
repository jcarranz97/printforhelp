"use client";

import { Card, Chip, Input, type Key, ListBox, Select } from "@heroui/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { PART_IMAGE_ASPECT_CSS } from "@/components/parts/part-image-field";
import { useI18n } from "@/i18n/provider";
import { markdownToExcerpt } from "@/lib/markdown-excerpt";
import type { Part } from "@/lib/parts.api";

const ALL = "all";

/** Reflect the active filters in the URL (e.g. ?search=hand&tag=splint) so a
 * filtered view is shareable. Uses history.replaceState so it does not re-run
 * the server component — filtering stays instant and client-side. */
function syncFilterUrl(search: string, tag: string): void {
  const params = new URLSearchParams();
  if (search.trim()) {
    params.set("search", search.trim());
  }
  if (tag !== ALL) {
    params.set("tag", tag);
  }
  const query = params.toString();
  const url = `${window.location.pathname}${query ? `?${query}` : ""}`;
  window.history.replaceState(null, "", url);
}

/**
 * Public Part catalog: a name search over a responsive grid of cards.
 * Each card shows the design's image (when present), tags, status, and a
 * link to download the source file.
 */
export function PartsCatalog({ parts }: { parts: Part[] }) {
  const { dict, locale } = useI18n();
  const t = dict.parts;
  const searchParams = useSearchParams();

  // Unique tags across the catalog, locale-sorted, for the filter dropdown.
  const tags = useMemo(
    () =>
      Array.from(new Set(parts.flatMap((p) => p.tags))).sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [parts, locale],
  );

  // Seed both filters from the URL (?search=..&tag=..) so shared links open
  // pre-filtered. The tag is accepted only when a part carries it, keeping
  // the controlled select in sync with its offered options.
  const [query, setQuery] = useState<string>(
    () => searchParams.get("search") ?? "",
  );
  const [tag, setTag] = useState<string>(() => {
    const value = searchParams.get("tag");
    return value && tags.includes(value) ? value : ALL;
  });

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return parts.filter(
      (p) =>
        (!q || p.name.toLowerCase().includes(q)) &&
        (tag === ALL || p.tags.includes(tag)),
    );
  }, [parts, query, tag]);

  function onQueryChange(value: string) {
    setQuery(value);
    syncFilterUrl(value, tag);
  }

  function onTagChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setTag(next);
    syncFilterUrl(query, next);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="w-full sm:w-72">
          <Input
            aria-label={t.search}
            placeholder={t.searchPlaceholder}
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
        {tags.length > 0 && (
          <div className="w-full sm:w-56">
            <Select
              aria-label={t.filterByTag}
              value={tag}
              onChange={onTagChange}
            >
              <Select.Trigger>
                <Select.Value />
                <Select.Indicator />
              </Select.Trigger>
              <Select.Popover>
                <ListBox>
                  <ListBox.Item id={ALL} textValue={t.allTags}>
                    {t.allTags}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                  {tags.map((tg) => (
                    <ListBox.Item key={tg} id={tg} textValue={tg}>
                      {tg}
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>
          </div>
        )}
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
            className="w-full rounded-t-2xl object-cover"
            style={{
              aspectRatio: PART_IMAGE_ASPECT_CSS,
              objectPosition: `${part.image_focus_x}% ${part.image_focus_y}%`,
            }}
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
