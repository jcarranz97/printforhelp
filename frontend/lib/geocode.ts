/** Thin client for OpenStreetMap's free Nominatim geocoder. */

export type GeocodeResult = {
  lat: number;
  lon: number;
};

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

// Cached results never expire automatically (addresses rarely move),
// but bump this if the cache format ever changes shape, to invalidate
// old entries.
const CACHE_PREFIX = "geocode-cache:v1:";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getCached(query: string): GeocodeResult | null {
  if (typeof window === "undefined") return null; // SSR guard
  try {
    const raw = window.localStorage.getItem(CACHE_PREFIX + query);
    if (!raw) return null;
    return JSON.parse(raw) as GeocodeResult;
  } catch {
    // Corrupt entry or localStorage unavailable (e.g. private browsing
    // in some browsers) — treat as a cache miss rather than failing.
    return null;
  }
}

function setCached(query: string, result: GeocodeResult) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CACHE_PREFIX + query, JSON.stringify(result));
  } catch {
    // Storage full or unavailable — safe to ignore, just means no
    // caching for this entry, not a functional failure.
  }
}

async function geocodeAddressUncached(
  query: string,
): Promise<GeocodeResult | null> {
  const params = new URLSearchParams({
    q: query,
    format: "json",
    limit: "1",
  });

  const res = await fetch(`${NOMINATIM_URL}?${params.toString()}`, {
    headers: {
      "Accept-Language": "en",
    },
  });

  if (!res.ok) {
    return null;
  }

  const data = (await res.json()) as Array<{ lat: string; lon: string }>;
  if (data.length === 0) {
    return null;
  }

  return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
}

export async function geocodeAddress(
  query: string,
): Promise<GeocodeResult | null> {
  const cached = getCached(query);
  if (cached) {
    return cached;
  }

  const result = await geocodeAddressUncached(query);
  if (result) {
    setCached(query, result);
  }
  return result;
}

/**
 * Geocode a batch of query strings and return results in the same
 * order, with `null` for addresses that failed to geocode. Cached
 * addresses resolve instantly and skip the rate limit entirely; only
 * uncached (new/changed) addresses hit the network, sequentially at
 * 1/sec to respect Nominatim's usage policy.
 */
export async function geocodeBatch(
  queries: string[],
): Promise<Array<GeocodeResult | null>> {
  const results: Array<GeocodeResult | null> = [];

  for (const query of queries) {
    const cached = getCached(query);
    if (cached) {
      results.push(cached);
      continue; // no delay needed — nothing was fetched over the network
    }

    try {
      const result = await geocodeAddressUncached(query);
      results.push(result);
      if (result) {
        setCached(query, result);
      }
    } catch {
      results.push(null);
    }

    await sleep(1100); // stay under Nominatim's 1 req/sec limit
  }

  return results;
}