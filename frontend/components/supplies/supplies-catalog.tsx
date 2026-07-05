"use client";

import { Card, Chip, Input, type Key, ListBox, Select } from "@heroui/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { useI18n } from "@/i18n/provider";
import { markdownToExcerpt } from "@/lib/markdown-excerpt";
import type { Supply } from "@/lib/supplies.api";

const ALL = "all";

/** Reflect the active filters in the URL (e.g. ?search=agua&tag=medico) so a
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
 * Public Supplies catalog: a name search over a responsive grid of cards.
 * Each card shows the supply's image (when present), tags, unit, and status.
 */
export function SuppliesCatalog({ supplies }: { supplies: Supply[] }) {
  const { dict, locale } = useI18n();
  const t = dict.supplies;
  const searchParams = useSearchParams();

  const tags = useMemo(
    () =>
      Array.from(new Set(supplies.flatMap((s) => s.tags))).sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [supplies, locale],
  );

  const [query, setQuery] = useState<string>(
    () => searchParams.get("search") ?? "",
  );
  const [tag, setTag] = useState<string>(() => {
    const value = searchParams.get("tag");
    return value && tags.includes(value) ? value : ALL;
  });

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return supplies.filter(
      (s) =>
        (!q || s.name.toLowerCase().includes(q)) &&
        (tag === ALL || s.tags.includes(tag)),
    );
  }, [supplies, query, tag]);

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
          {filtered.map((supply) => (
            <SupplyCard key={supply.id} supply={supply} />
          ))}
        </div>
      )}
    </div>
  );
}

function SupplyCard({ supply }: { supply: Supply }) {
  const { dict } = useI18n();
  const t = dict.supplies;
  return (
    <Link
      href={`/supplies/${supply.id}`}
      className="rounded-2xl transition-shadow hover:shadow-md"
      aria-label={`${t.viewDetails} ${supply.name}`}
    >
      <Card className="h-full">
        {supply.image_url && (
          // External, user-supplied image URL: next/image would need every
          // host allow-listed, so a plain img is the pragmatic choice here.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={supply.image_url}
            alt={supply.name}
            className="h-40 w-full rounded-t-2xl object-cover"
          />
        )}
        <Card.Header>
          <Card.Title>{supply.name}</Card.Title>
          {supply.description && (
            <Card.Description className="line-clamp-2">
              {markdownToExcerpt(supply.description)}
            </Card.Description>
          )}
        </Card.Header>
        <Card.Content className="flex flex-col gap-2 text-sm">
          {supply.units.length > 0 && (
            <span className="text-muted">
              {t.units}: <strong>{supply.units.join(", ")}</strong>
            </span>
          )}
          {supply.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {supply.tags.map((tag) => (
                <Chip key={tag} variant="soft" size="sm">
                  {tag}
                </Chip>
              ))}
            </div>
          )}
        </Card.Content>
        <Card.Footer>
          {supply.status === "discontinued" && (
            <Chip color="warning" variant="soft" size="sm">
              {t.discontinued}
            </Chip>
          )}
        </Card.Footer>
      </Card>
    </Link>
  );
}
