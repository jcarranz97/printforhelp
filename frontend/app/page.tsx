import Link from "next/link";
import { FaDiscord, FaWhatsapp } from "react-icons/fa";

import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import {
  COMMUNITY_DISCORD_URL,
  MAP_DISAIN_URL,
  MAP_USHAHIDI_URL,
  WHATSAPP_EN_URL,
  WHATSAPP_ES_URL,
} from "@/lib/links";

const PRIMARY_PILL =
  "inline-flex items-center gap-2 self-start rounded-full px-4 py-2 " +
  "text-sm font-medium text-white transition-opacity hover:opacity-90";
const SECONDARY_PILL =
  "inline-flex items-center gap-2 self-start rounded-full border px-4 py-2 " +
  "text-sm font-medium transition-opacity hover:opacity-90";

type Announcement = Dictionary["landing"]["announcement"];

// UTC ("generic worldwide" time). Stored in ISO 8601; rendered per-locale
// with the UTC label so it reads the same anywhere. When announcements
// become data-driven, this comes from the record's timestamp instead.
const ANNOUNCEMENT_PUBLISHED_AT = "2026-06-30T05:00:00Z";

export default async function LandingPage() {
  const { dict, locale } = await getServerI18n();
  const t = dict.landing;
  const h = t.help;

  const announcementPublishedDisplay = new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(new Date(ANNOUNCEMENT_PUBLISHED_AT));

  return (
    <main>
      <section className="mx-auto max-w-5xl px-6 pt-24 pb-16 text-center">
        <p
          className="text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--accent)" }}
        >
          {t.eyebrow}
        </p>
        <h1 className="mt-4 text-5xl font-bold leading-tight sm:text-6xl">
          {t.title}
        </h1>
        <p
          className="mx-auto mt-6 max-w-2xl text-lg sm:text-xl"
          style={{ color: "var(--muted)" }}
        >
          {t.subtitle}
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <a
            href="#how-it-works"
            className="rounded-full px-6 py-3 font-medium text-white transition-opacity hover:opacity-90"
            style={{ background: "var(--accent-strong)" }}
          >
            {t.howItWorks}
          </a>
          <a
            href="#help"
            className="rounded-full border px-6 py-3 font-medium transition-colors hover:bg-black/5"
            style={{
              borderColor: "var(--card-border)",
              color: "var(--foreground)",
            }}
          >
            {t.wantToHelp}
          </a>
        </div>
      </section>

      <section
        id="announcements"
        className="mx-auto max-w-5xl px-6 pb-8"
        aria-label={t.announcementsAriaLabel}
      >
        <AnnouncementCard
          a={t.announcement}
          id="print-standards"
          publishedAt={ANNOUNCEMENT_PUBLISHED_AT}
          publishedDisplay={announcementPublishedDisplay}
        />
      </section>

      <section
        id="features"
        className="mx-auto max-w-5xl px-6 pt-8 pb-16"
        aria-label={t.featuresAriaLabel}
      >
        <div className="grid gap-6 sm:grid-cols-3">
          <FeatureCard
            title={t.centersTitle}
            description={t.centersDescription}
            href="/centers"
          />
          <FeatureCard
            title={t.requestsTitle}
            description={t.requestsDescription}
            href="/requests"
          />
          <FeatureCard
            title={t.printingTitle}
            description={t.printingDescription}
            href="/parts"
          />
        </div>
      </section>

      <section
        id="how-it-works"
        className="scroll-mt-20 border-t py-20"
        style={{ borderColor: "var(--card-border)" }}
      >
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-3xl font-bold">{t.howItWorksHeading}</h2>
          <p
            className="mt-4 max-w-2xl text-lg"
            style={{ color: "var(--muted)" }}
          >
            {t.howItWorksIntro}
          </p>
          <div className="mt-10 grid gap-6 sm:grid-cols-3">
            <StepCard step={1} title={t.step1Title} body={t.step1Body} />
            <StepCard step={2} title={t.step2Title} body={t.step2Body} />
            <StepCard step={3} title={t.step3Title} body={t.step3Body} />
          </div>
        </div>
      </section>

      <section
        id="help"
        className="scroll-mt-20 border-t py-20"
        style={{ borderColor: "var(--card-border)" }}
      >
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-3xl font-bold">{h.heading}</h2>
          <p
            className="mt-4 max-w-3xl text-lg"
            style={{ color: "var(--muted)" }}
          >
            {h.intro}
          </p>
          <p
            className="mt-3 max-w-3xl text-sm"
            style={{ color: "var(--muted)" }}
          >
            {h.quakeNote}
          </p>

          <h3 className="mt-12 text-xl font-semibold">{h.stepsHeading}</h3>
          <p
            className="mt-2 max-w-3xl text-sm"
            style={{ color: "var(--muted)" }}
          >
            {h.stepsIntro}
          </p>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <GuideCard
              title={h.printTitle}
              body={h.printBody}
              tags={h.printTags}
              caution={{
                text: h.printCaution,
                cta: h.printCautionCta,
                href: h.printCautionHref,
              }}
            >
              <Link
                href={h.printCtaHref}
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                {h.printCta}
              </Link>
            </GuideCard>

            <GuideCard title={h.qualityTitle} body={h.qualityBody}>
              <a
                href="#print-standards"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                {h.qualityCta}
              </a>
            </GuideCard>

            <GuideCard
              title={h.packTitle}
              body={h.packBody}
              bullets={h.packChecklist}
              note={h.packNote}
            >
              <Link
                href="/parts"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                {h.packAllCta}
              </Link>
              <Link
                href={h.printCtaHref}
                className={SECONDARY_PILL}
                style={{
                  borderColor: "var(--card-border)",
                  color: "var(--accent-strong)",
                }}
              >
                {h.printCta}
              </Link>
            </GuideCard>

            <GuideCard title={h.deliverTitle} body={h.deliverBody}>
              <Link
                href="/centers"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                {h.deliverCentersCta}
              </Link>
              <a
                href={MAP_USHAHIDI_URL}
                target="_blank"
                rel="noreferrer"
                className={SECONDARY_PILL}
                style={{
                  borderColor: "var(--card-border)",
                  color: "var(--accent-strong)",
                }}
              >
                {h.mapUshahidiLabel}
              </a>
              <a
                href={MAP_DISAIN_URL}
                target="_blank"
                rel="noreferrer"
                className={SECONDARY_PILL}
                style={{
                  borderColor: "var(--card-border)",
                  color: "var(--accent-strong)",
                }}
              >
                {h.mapDisainLabel}
              </a>
            </GuideCard>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2">
            <GuideCard
              title={h.noPrinterTitle}
              body={h.noPrinterBody}
              bullets={h.noPrinterList}
            >
              <a
                href="#community"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                {h.noPrinterCta}
              </a>
            </GuideCard>

            <GuideCard title={h.aboutTitle} body={h.aboutBody} />
          </div>

          <h3
            id="community"
            className="mt-12 scroll-mt-20 text-xl font-semibold"
          >
            {h.communityHeading}
          </h3>
          <p
            className="mt-2 max-w-3xl text-sm"
            style={{ color: "var(--muted)" }}
          >
            {h.communityIntro}
          </p>
          <div className="mt-6 grid gap-6 md:grid-cols-3">
            <GuideCard title={h.whatsappEsTitle} body={h.whatsappEsBody}>
              <a
                href={WHATSAPP_ES_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaWhatsapp aria-hidden className="h-4 w-4" />
                {h.communityJoinCta}
              </a>
            </GuideCard>

            <GuideCard title={h.whatsappEnTitle} body={h.whatsappEnBody}>
              <a
                href={WHATSAPP_EN_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaWhatsapp aria-hidden className="h-4 w-4" />
                {h.communityJoinCta}
              </a>
            </GuideCard>

            <GuideCard title={h.discordTitle} body={h.discordBody}>
              <a
                href={COMMUNITY_DISCORD_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaDiscord aria-hidden className="h-4 w-4" />
                {h.communityJoinCta}
              </a>
            </GuideCard>
          </div>
        </div>
      </section>
    </main>
  );
}

function StepCard({
  step,
  title,
  body,
}: {
  step: number;
  title: string;
  body: string;
}) {
  return (
    <div
      className="h-full rounded-2xl border p-6"
      style={{ background: "var(--card)", borderColor: "var(--card-border)" }}
    >
      <span
        aria-hidden
        className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white"
        style={{ background: "var(--accent-strong)" }}
      >
        {step}
      </span>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-3 text-sm" style={{ color: "var(--muted)" }}>
        {body}
      </p>
    </div>
  );
}

function GuideCard({
  title,
  body,
  bullets,
  tags,
  note,
  caution,
  children,
}: {
  title: string;
  body: string;
  bullets?: ReadonlyArray<string>;
  tags?: ReadonlyArray<{ label: string; href: string }>;
  note?: string;
  caution?: { text: string; cta: string; href: string };
  children?: React.ReactNode;
}) {
  return (
    <div
      className="flex h-full flex-col rounded-2xl border p-6"
      style={{ background: "var(--card)", borderColor: "var(--card-border)" }}
    >
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-3 text-sm" style={{ color: "var(--muted)" }}>
        {body}
      </p>
      {bullets && (
        <ul
          className="mt-3 list-disc space-y-1.5 pl-5 text-sm"
          style={{ color: "var(--muted)" }}
        >
          {bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      {tags && (
        <div className="mt-3 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <Link
              key={tag.href}
              href={tag.href}
              className="rounded-full border px-3 py-1 text-xs font-medium transition-opacity hover:opacity-90"
              style={{
                borderColor: "var(--card-border)",
                color: "var(--accent-strong)",
              }}
            >
              {tag.label}
            </Link>
          ))}
        </div>
      )}
      {caution && (
        <div
          className="mt-3 rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: "color-mix(in srgb, #f59e0b 45%, var(--card-border))",
            background: "color-mix(in srgb, #f59e0b 10%, transparent)",
            color: "var(--muted)",
          }}
        >
          {caution.text}{" "}
          <Link
            href={caution.href}
            className="font-medium underline"
            style={{ color: "var(--accent-strong)" }}
          >
            {caution.cta}
          </Link>
        </div>
      )}
      {note && (
        <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
          {note}
        </p>
      )}
      {children && (
        <div className="mt-4 flex flex-1 flex-wrap items-end gap-3">
          {children}
        </div>
      )}
    </div>
  );
}

type FeatureCardProps = {
  title: string;
  description: string;
  badge?: string;
  href?: string;
};

function FeatureCard({ title, description, badge, href }: FeatureCardProps) {
  const card = (
    <div
      className="h-full rounded-2xl border p-6 transition-shadow hover:shadow-md"
      style={{
        background: "var(--card)",
        borderColor: "var(--card-border)",
      }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{title}</h3>
        {badge && (
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              background: "color-mix(in srgb, var(--accent) 12%, transparent)",
              color: "var(--accent-strong)",
            }}
          >
            {badge}
          </span>
        )}
      </div>
      <p className="mt-3 text-sm" style={{ color: "var(--muted)" }}>
        {description}
      </p>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {card}
      </Link>
    );
  }
  return card;
}

function AnnouncementCard({
  a,
  id,
  publishedAt,
  publishedDisplay,
}: {
  a: Announcement;
  id: string;
  publishedAt: string;
  publishedDisplay: string;
}) {
  return (
    <article
      id={id}
      className="scroll-mt-24 rounded-2xl border p-6 sm:p-8"
      style={{
        background: "var(--card)",
        borderColor:
          "color-mix(in srgb, var(--accent) 35%, var(--card-border))",
      }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider"
          style={{
            background: "color-mix(in srgb, var(--accent) 14%, transparent)",
            color: "var(--accent-strong)",
          }}
        >
          {a.tag}
        </span>
        <span
          className="rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider"
          style={{
            background: "color-mix(in srgb, #ef4444 16%, transparent)",
            color: "#ef4444",
          }}
        >
          {a.priority}
        </span>
      </div>

      <p className="mt-3 text-xs" style={{ color: "var(--muted)" }}>
        {a.publishedLabel}{" "}
        <time dateTime={publishedAt} className="font-medium">
          {publishedDisplay}
        </time>
      </p>

      <h2 className="mt-3 text-2xl font-bold sm:text-3xl">
        <a
          href={`#${id}`}
          className="group inline-flex items-start gap-2 hover:underline"
          aria-label={`${a.title} — ${a.permalinkLabel}`}
        >
          <span>{a.title}</span>
          <span
            aria-hidden
            className="mt-1 text-xl opacity-0 transition-opacity group-hover:opacity-60"
            style={{ color: "var(--accent-strong)" }}
            title={a.permalinkLabel}
          >
            #
          </span>
        </a>
      </h2>
      <p className="mt-3 max-w-3xl text-base" style={{ color: "var(--muted)" }}>
        {a.summary}
      </p>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <SpecGroup
          heading={a.materialsHeading}
          items={a.materialsUse}
          accent="var(--accent-strong)"
        />
        <SpecGroup
          heading={a.avoidHeading}
          items={a.materialsAvoid}
          accent="#ef4444"
        />
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold">{a.settingsHeading}</h3>
        <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
          {a.settings.map((s) => (
            <div
              key={s.label}
              className="flex flex-wrap justify-between gap-x-4 border-b py-1 text-sm"
              style={{ borderColor: "var(--card-border)" }}
            >
              <dt style={{ color: "var(--muted)" }}>{s.label}</dt>
              <dd className="font-medium">{s.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </article>
  );
}

function SpecGroup({
  heading,
  items,
  accent,
}: {
  heading: string;
  items: ReadonlyArray<{ label: string; value: string }>;
  accent: string;
}) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{
        borderColor: "var(--card-border)",
        background: "color-mix(in srgb, var(--foreground) 3%, transparent)",
      }}
    >
      <h3 className="text-sm font-semibold" style={{ color: accent }}>
        {heading}
      </h3>
      <ul className="mt-3 space-y-2 text-sm">
        {items.map((item) => (
          <li key={item.label}>
            <span className="font-semibold">{item.label}:</span>{" "}
            <span style={{ color: "var(--muted)" }}>{item.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
