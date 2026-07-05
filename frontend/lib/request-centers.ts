/** Build the drop-off center options for the request forms (server-side).
 *
 * Merges the public verified+active directory with the caller's own centers
 * (listed + their private, request-specific locations), de-duplicated by id,
 * so a requester can pick public centers, reuse their private ones, or add a
 * new private location inline.
 */

import type { CenterOption } from "@/components/requests/preferred-centers-field";
import {
  getCollectionCenter,
  listCollectionCenters,
  listMyCollectionCenters,
} from "@/lib/collection-centers.api";

export async function requestCenterOptions(
  token: string,
  /** Extra center ids to guarantee in the list (e.g. a request's currently
   * selected private centers, which the editor may not own). */
  includeIds: string[] = [],
): Promise<CenterOption[]> {
  const [publicCenters, myCenters] = await Promise.all([
    listCollectionCenters({ verified: true }),
    token ? listMyCollectionCenters(token) : Promise.resolve([]),
  ]);
  const byId = new Map<string, CenterOption>();
  for (const c of publicCenters) {
    if (c.status === "active") {
      byId.set(c.id, {
        id: c.id,
        name: c.name,
        city: c.city,
        country: c.country,
        listed: c.listed,
      });
    }
  }
  // The caller's own centers (incl. private, unlisted) — override/extend.
  for (const c of myCenters) {
    byId.set(c.id, {
      id: c.id,
      name: c.name,
      city: c.city,
      country: c.country,
      listed: c.listed,
    });
  }
  // Ensure any already-selected centers are present so they render as checked.
  const missing = includeIds.filter((cid) => !byId.has(cid));
  const fetched = await Promise.all(
    missing.map((cid) => getCollectionCenter(cid)),
  );
  for (const c of fetched) {
    if (c) {
      byId.set(c.id, {
        id: c.id,
        name: c.name,
        city: c.city,
        country: c.country,
        listed: c.listed,
      });
    }
  }
  return Array.from(byId.values());
}
