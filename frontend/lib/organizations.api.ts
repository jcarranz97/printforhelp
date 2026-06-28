/** Raw API calls for the organizations directory (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type OrganizationStatus = "active" | "inactive";

export type Organization = {
  id: string;
  name: string;
  description: string | null;
  contact: string;
  website: string | null;
  country: string;
  verified: boolean;
  registered_by_id: string;
  verified_by_id: string | null;
  status: OrganizationStatus;
  active: boolean;
  created_at: string;
  updated_at: string;
};

/**
 * Fetch a single organization by id. Returns null when the org is not
 * found or is not publicly visible — unverified orgs are hidden from
 * guests (FR-105), which callers render as an "unverified" badge.
 */
export async function getOrganization(
  id: string,
): Promise<Organization | null> {
  const res = await fetch(`${apiBaseUrl()}/organizations/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Organization;
}
