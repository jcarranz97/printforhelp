import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { GenerateTrackingButton } from "@/components/tracking/generate-tracking-button";
import { RecordTimeline } from "@/components/tracking/record-timeline";
import { ShareLink } from "@/components/tracking/share-link";
import { TrackingSettingsForm } from "@/components/tracking/tracking-settings-form";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import {
  type OwnerTracking,
  getOwnerTracking,
  trackQrImageUrl,
} from "@/lib/tracking.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.tracking.pageTitle} · PrintForHelp` };
}

export default async function TrackingManagePage({
  params,
}: {
  params: Promise<{ contributionId: string }>;
}) {
  const { contributionId } = await params;
  const path = `/my-contributions/${contributionId}/tracking`;
  const user = await getCurrentUser();
  if (!user) {
    redirect(`/login?next=${path}`);
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value ?? "";
  const { dict } = await getServerI18n();
  const t = dict.tracking;

  let tracking: OwnerTracking | null = null;
  try {
    tracking = await getOwnerTracking(contributionId, token);
  } catch (error) {
    // 404 = not generated yet → show the generate prompt. Anything else
    // (e.g. 403 not the maker) is a real not-found for this user.
    if (error instanceof ApiError && error.status === 404) {
      tracking = null;
    } else {
      notFound();
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link
        href="/my-contributions"
        className="text-sm text-muted hover:underline"
      >
        ← {t.backToContributions}
      </Link>
      <h1 className="mt-2 text-2xl font-bold">{t.pageTitle}</h1>

      {tracking === null ? (
        <div className="mt-8">
          <GenerateTrackingButton contributionId={contributionId} />
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-10">
          <section className="flex items-start gap-4">
            {tracking.resource_image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={tracking.resource_image_url}
                alt={tracking.resource_name}
                className="h-16 w-16 rounded-lg object-cover"
              />
            )}
            <div>
              <p className="font-semibold">{tracking.resource_name}</p>
              <p className="text-sm text-muted">
                {t.summaryQuantity}: {tracking.quantity}
              </p>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">{t.settingsTitle}</h2>
            <TrackingSettingsForm
              groupId={tracking.group_id}
              contributionId={contributionId}
              visibility={tracking.visibility}
              members={tracking.members.map((m) => m.username)}
            />
          </section>

          <section>
            <ShareLink
              token={tracking.tracking_token}
              visibility={tracking.visibility}
            />
          </section>

          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <h2 className="text-lg font-semibold">{t.qrTitle}</h2>
              <p className="text-sm text-muted">{t.qrDescription}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href={`/tracking-bundle/${tracking.group_id}?format=pdf`}
                className="rounded-lg bg-[var(--accent-strong)] px-4 py-2 text-sm font-medium text-white"
                prefetch={false}
              >
                {t.downloadPdf}
              </Link>
              <Link
                href={`/tracking-bundle/${tracking.group_id}?format=png`}
                className="rounded-lg border border-[var(--card-border)] px-4 py-2 text-sm font-medium"
                prefetch={false}
              >
                {t.downloadPng}
              </Link>
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <QrCard
                token={tracking.tracking_token}
                caption={t.groupLabel}
                downloadLabel={t.downloadQr}
                openLabel={t.openPublicPage}
              />
              {tracking.items.map((item) => (
                <QrCard
                  key={item.id}
                  token={item.tracking_token}
                  caption={`${t.itemLabel} #${item.sequence}`}
                  downloadLabel={t.downloadQr}
                  openLabel={t.openPublicPage}
                />
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">{t.timelineTitle}</h2>
            <RecordTimeline
              records={tracking.records}
              revalidate={path}
              showItemSequence
            />
          </section>
        </div>
      )}
    </main>
  );
}

/** One QR thumbnail with a download link and a link to its public page. */
function QrCard({
  token,
  caption,
  downloadLabel,
  openLabel,
}: {
  token: string;
  caption: string;
  downloadLabel: string;
  openLabel: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border border-[var(--card-border)] p-3 text-center">
      <span className="text-xs font-medium">{caption}</span>
      {/* Unauthenticated QR endpoint, fetched directly by the browser. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={trackQrImageUrl(token)} alt={caption} className="h-28 w-28" />
      <div className="flex flex-col gap-0.5 text-xs">
        <a
          href={trackQrImageUrl(token)}
          download
          className="text-[var(--accent-strong)] hover:underline"
        >
          {downloadLabel}
        </a>
        <Link
          href={`/track/${token}`}
          className="text-muted hover:underline"
          prefetch={false}
        >
          {openLabel}
        </Link>
      </div>
    </div>
  );
}
