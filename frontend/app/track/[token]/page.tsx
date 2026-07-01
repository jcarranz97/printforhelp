import type { Metadata } from "next";
import { cookies } from "next/headers";

import { getCurrentUser } from "@/actions/auth.action";
import { AddRecordForm } from "@/components/tracking/add-record-form";
import { RecordTimeline } from "@/components/tracking/record-timeline";
import { ScopeToggle } from "@/components/tracking/scope-toggle";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { type ContributionStatus } from "@/lib/contributions.api";
import {
  type PublicTracking,
  getPublicTracking,
  trackQrImageUrl,
} from "@/lib/tracking.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.tracking.pageTitle} · PrintForHelp` };
}

export default async function PublicTrackingPage({
  params,
  searchParams,
}: {
  params: Promise<{ token: string }>;
  searchParams: Promise<{ items?: string }>;
}) {
  const { token } = await params;
  const { items } = await searchParams;
  // Group timelines fold in item updates by default; `?items=group` narrows it.
  const includeItems = items !== "group";
  const authToken = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const t = dict.tracking;

  let tracking: PublicTracking | null = null;
  let forbidden = false;
  let missing = false;
  try {
    tracking = await getPublicTracking(token, authToken, includeItems);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      forbidden = true;
    } else {
      missing = true;
    }
  }

  if (forbidden || missing) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16 text-center">
        <h1 className="text-xl font-bold">
          {forbidden ? t.privateTitle : t.notFoundTitle}
        </h1>
        <p className="mt-2 text-sm text-muted">
          {forbidden ? t.privateBody : t.notFoundBody}
        </p>
      </main>
    );
  }

  // `tracking` is set here (both error flags are false).
  const data = tracking as PublicTracking;
  const statusLabels = dict.myContributions.status;
  const statusLabel =
    statusLabels[data.contribution_status as ContributionStatus] ??
    data.contribution_status;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <section className="flex items-start gap-4">
        {data.resource_image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={data.resource_image_url}
            alt={data.resource_name}
            className="h-20 w-20 rounded-lg object-cover"
          />
        )}
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold">{data.resource_name}</h1>
          <p className="text-sm text-muted">
            {data.target_kind === "item" && data.item_sequence !== null
              ? `${t.itemLabel} #${data.item_sequence}`
              : t.groupLabel}
          </p>
          <p className="text-sm text-muted">
            {t.summaryStatus}: {statusLabel}
          </p>
        </div>
      </section>

      <section className="mt-6 flex flex-col items-center gap-2">
        {/* Unauthenticated QR endpoint, fetched directly by the browser. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={trackQrImageUrl(data.tracking_token)}
          alt={t.pageTitle}
          className="h-32 w-32"
        />
      </section>

      {data.can_contribute && (
        <section className="mt-8 flex flex-col gap-3">
          <h2 className="text-lg font-semibold">{t.addUpdateTitle}</h2>
          <AddRecordForm
            trackingToken={data.tracking_token}
            isLoggedIn={user !== null}
            suggestions={Array.from(
              new Set(data.records.flatMap((r) => r.tags)),
            )}
          />
        </section>
      )}

      <section className="mt-10 flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t.timelineTitle}</h2>
        {data.target_kind === "group" && (
          <ScopeToggle includeItems={includeItems} />
        )}
        <RecordTimeline
          records={data.records}
          revalidate={`/track/${token}`}
          showItemSequence={data.target_kind === "group"}
        />
      </section>
    </main>
  );
}
