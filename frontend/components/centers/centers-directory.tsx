"use client";

import { Card, Chip, type Key, ListBox, Select } from "@heroui/react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useI18n } from "@/i18n/provider";
import type { CollectionCenter } from "@/lib/collection-centers.api";

const ALL = "all";

/** Sorted unique values for a string field, using locale-aware order. */
function uniqueSorted(values: string[], locale: string): string[] {
  return Array.from(new Set(values)).sort((a, b) =>
    a.localeCompare(b, locale, { sensitivity: "base" }),
  );
}

/**
 * Public Collection Centers directory: a country/city filter bar over a
 * responsive grid of center cards. Filtering happens client-side over the
 * full verified-active set so it stays instant and deep-link-free for v1.
 */
export function CentersDirectory({ centers }: { centers: CollectionCenter[] }) {
  const { locale, dict } = useI18n();
  const t = dict.centers;
  const [country, setCountry] = useState<string>(ALL);
  const [city, setCity] = useState<string>(ALL);

  const countries = useMemo(
    () =>
      uniqueSorted(
        centers.map((c) => c.country),
        locale,
      ),
    [centers, locale],
  );

  const cities = useMemo(() => {
    const pool =
      country === ALL ? centers : centers.filter((c) => c.country === country);
    return uniqueSorted(
      pool.map((c) => c.city),
      locale,
    );
  }, [centers, country, locale]);

  const filtered = useMemo(
    () =>
      centers.filter(
        (c) =>
          (country === ALL || c.country === country) &&
          (city === ALL || c.city === city),
      ),
    [centers, country, city],
  );

  function onCountryChange(value: Key | null) {
    setCountry(value === null ? ALL : String(value));
    setCity(ALL);
  }

  function onCityChange(value: Key | null) {
    setCity(value === null ? ALL : String(value));
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="w-full sm:w-56">
          <Select
            aria-label={t.filterByCountry}
            value={country}
            onChange={onCountryChange}
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id={ALL} textValue={t.allCountries}>
                  {t.allCountries}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                {countries.map((c) => (
                  <ListBox.Item key={c} id={c} textValue={c}>
                    {c}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>

        <div className="w-full sm:w-56">
          <Select
            aria-label={t.filterByCity}
            value={city}
            onChange={onCityChange}
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id={ALL} textValue={t.allCities}>
                  {t.allCities}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                {cities.map((c) => (
                  <ListBox.Item key={c} id={c} textValue={c}>
                    {c}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>

        <p className="text-sm text-muted sm:ml-auto sm:pb-2">
          {filtered.length} {filtered.length === 1 ? t.countOne : t.countOther}
        </p>
      </div>

      {filtered.length === 0 ? (
        <Card variant="transparent" className="py-12 text-center">
          <Card.Content>
            <p className="text-muted">{t.empty}</p>
          </Card.Content>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((center) => (
            <CenterCard key={center.id} center={center} />
          ))}
        </div>
      )}
    </div>
  );
}

function CenterCard({ center }: { center: CollectionCenter }) {
  const { dict } = useI18n();
  const t = dict.centers;
  return (
    <Link
      href={`/centers/${center.id}`}
      className="rounded-2xl transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2"
      aria-label={`${t.viewDetails} ${center.name}`}
    >
      <Card className="h-full">
        <Card.Header>
          <Card.Title>{center.name}</Card.Title>
          <Card.Description>
            {center.city}, {center.country}
          </Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-1 text-sm">
          <span className="text-muted">{center.address}</span>
          <span className="font-medium">{center.contact}</span>
          {center.opening_hours && (
            <span className="text-muted">{center.opening_hours}</span>
          )}
        </Card.Content>
        <Card.Footer>
          {center.verified ? (
            <Chip color="success" variant="soft" size="sm">
              {t.verified}
            </Chip>
          ) : (
            <Chip color="warning" variant="soft" size="sm">
              {t.unverified}
            </Chip>
          )}
        </Card.Footer>
      </Card>
    </Link>
  );
}
