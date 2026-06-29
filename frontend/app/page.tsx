import Link from "next/link";

import { getServerI18n } from "@/i18n/server";

export default async function LandingPage() {
  const { dict } = await getServerI18n();
  const t = dict.landing;

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
            <StepCard title={t.step1Title} body={t.step1Body} />
            <StepCard title={t.step2Title} body={t.step2Body} />
            <StepCard title={t.step3Title} body={t.step3Body} />
          </div>
        </div>
      </section>

      <section
        id="help"
        className="scroll-mt-20 border-t py-20"
        style={{ borderColor: "var(--card-border)" }}
      >
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-3xl font-bold">{t.helpHeading}</h2>
          <p
            className="mt-4 max-w-2xl text-lg"
            style={{ color: "var(--muted)" }}
          >
            {t.helpIntro}
          </p>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            <HelpCard
              title={t.helpCenterTitle}
              body={t.helpCenterBody}
              cta={t.helpCenterCta}
              href="/centers/new"
            />
            <HelpCard
              title={t.helpMakerTitle}
              body={t.helpMakerBody}
              cta={t.helpMakerCta}
              href="/requests"
            />
            <HelpCard
              title={t.helpDevTitle}
              body={t.helpDevBody}
              cta={t.helpDevCta}
              href="/about#contribute"
            />
          </div>
        </div>
      </section>
    </main>
  );
}

function StepCard({ title, body }: { title: string; body: string }) {
  return (
    <div
      className="h-full rounded-2xl border p-6"
      style={{ background: "var(--card)", borderColor: "var(--card-border)" }}
    >
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-3 text-sm" style={{ color: "var(--muted)" }}>
        {body}
      </p>
    </div>
  );
}

function HelpCard({
  title,
  body,
  cta,
  href,
}: {
  title: string;
  body: string;
  cta: string;
  href: string;
}) {
  return (
    <div
      className="flex h-full flex-col rounded-2xl border p-6"
      style={{ background: "var(--card)", borderColor: "var(--card-border)" }}
    >
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-3 flex-1 text-sm" style={{ color: "var(--muted)" }}>
        {body}
      </p>
      <Link
        href={href}
        className="mt-4 inline-block self-start rounded-full px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        style={{ background: "var(--accent-strong)" }}
      >
        {cta}
      </Link>
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
