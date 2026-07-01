/** Thin client for OpenStreetMap's free Nominatim geocoder. */

export type GeocodeResult = {
  lat: number;
  lon: number;
};

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

// Nominatim's usage policy caps automated use at 1 request/second.
// We geocode sequentially with a small delay instead of firing all
// requests in parallel, to stay within that limit and avoid getting
// rate-limited or blocked.
function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function geocodeAddress(
  query: string,
): Promise<GeocodeResult | null> {
  const params = new URLSearchParams({
    q: query,
    format: "json",
    limit: "1",
  });

  const res = await fetch(`${NOMINATIM_URL}?${params.toString()}`, {
    headers: {
      // Nominatim's usage policy asks for an identifiable client;
      // browsers send Referer automatically, this is a courtesy extra.
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

/**
 * Geocode a batch of query strings sequentially (1/sec) and return
 * results in the same order, with `null` for addresses that failed
 * to geocode.
 */
export async function geocodeBatch(
  queries: string[],
): Promise<Array<GeocodeResult | null>> {
  const results: Array<GeocodeResult | null> = [];
  for (const query of queries) {
    try {
      results.push(await geocodeAddress(query));
    } catch {
      results.push(null);
    }
    await sleep(1100); // stay under Nominatim's 1 req/sec limit
  }
  return results;
}