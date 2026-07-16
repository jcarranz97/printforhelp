import Link from "next/link";
import { FaDiscord, FaInstagram, FaWhatsapp } from "react-icons/fa";

import { getServerI18n } from "@/i18n/server";
import {
  COMMUNITY_DISCORD_URL,
  INSTAGRAM_URL,
  WHATSAPP_EN_URL,
  WHATSAPP_ES_URL,
  WHATSAPP_USA_URL,
} from "@/lib/links";

const PRIMARY_PILL =
  "inline-flex items-center gap-2 self-start rounded-full px-4 py-2 " +
  "text-sm font-medium text-white transition-opacity hover:opacity-90";

export default async function LandingPage() {
  const { dict } = await getServerI18n();
  const t = dict.landing;
  const c = t.community;

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
          <Link
            href="/requests"
            className="rounded-full border px-6 py-3 font-medium transition-colors hover:bg-black/5"
            style={{
              borderColor: "var(--card-border)",
              color: "var(--foreground)",
            }}
          >
            {t.wantToHelp}
          </Link>
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
        id="community"
        className="scroll-mt-20 border-t py-20"
        style={{ borderColor: "var(--card-border)" }}
      >
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-3xl font-bold">{c.heading}</h2>
          <p
            className="mt-4 max-w-3xl text-lg"
            style={{ color: "var(--muted)" }}
          >
            {c.intro}
          </p>
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <ChannelCard title={c.whatsappEsTitle} body={c.whatsappEsBody}>
              <a
                href={WHATSAPP_ES_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaWhatsapp aria-hidden className="h-4 w-4" />
                {c.joinCta}
              </a>
            </ChannelCard>

            <ChannelCard title={c.whatsappUsaTitle} body={c.whatsappUsaBody}>
              <a
                href={WHATSAPP_USA_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaWhatsapp aria-hidden className="h-4 w-4" />
                {c.joinCta}
              </a>
            </ChannelCard>

            <ChannelCard title={c.whatsappEnTitle} body={c.whatsappEnBody}>
              <a
                href={WHATSAPP_EN_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaWhatsapp aria-hidden className="h-4 w-4" />
                {c.joinCta}
              </a>
            </ChannelCard>

            <ChannelCard title={c.discordTitle} body={c.discordBody}>
              <a
                href={COMMUNITY_DISCORD_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaDiscord aria-hidden className="h-4 w-4" />
                {c.joinCta}
              </a>
            </ChannelCard>

            <ChannelCard title={c.instagramTitle} body={c.instagramBody}>
              <a
                href={INSTAGRAM_URL}
                target="_blank"
                rel="noreferrer"
                className={PRIMARY_PILL}
                style={{ background: "var(--accent-strong)" }}
              >
                <FaInstagram aria-hidden className="h-4 w-4" />
                {c.followCta}
              </a>
            </ChannelCard>
          </div>
        </div>
      </section>
    </main>
  );
}

function ChannelCard({
  title,
  body,
  children,
}: {
  title: string;
  body: string;
  children: React.ReactNode;
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
      <div className="mt-4 flex flex-1 flex-wrap items-end gap-3">
        {children}
      </div>
    </div>
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
