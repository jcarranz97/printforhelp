import Link from "next/link";

import { getServerI18n } from "@/i18n/server";

export default async function LandingPage() {
  const { dict } = await getServerI18n();
  const t = dict.landing;

  return (
    <main className="min-h-screen">
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
            href="#features"
            className="rounded-full px-6 py-3 font-medium text-white transition-opacity hover:opacity-90"
            style={{ background: "var(--accent-strong)" }}
          >
            {t.howItWorks}
          </a>
          <button
            type="button"
            className="rounded-full border px-6 py-3 font-medium transition-colors hover:bg-black/5"
            style={{
              borderColor: "var(--card-border)",
              color: "var(--foreground)",
            }}
          >
            {t.wantToHelp}
          </button>
        </div>
      </section>

      <section
        id="features"
        className="mx-auto max-w-5xl px-6 pt-8 pb-24"
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
            badge={t.comingSoon}
          />
          <FeatureCard
            title={t.printingTitle}
            description={t.printingDescription}
            badge={t.comingSoon}
          />
        </div>
      </section>

      <footer
        className="border-t py-8 text-center text-sm"
        style={{
          borderColor: "var(--card-border)",
          color: "var(--muted)",
        }}
      >
        <p>{t.footer}</p>
      </footer>
    </main>
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
