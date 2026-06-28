import { getServerI18n } from "@/i18n/server";

/**
 * Global site footer shown on every page. Server component so it can read
 * the active locale dictionary directly.
 */
export async function Footer() {
  const { dict } = await getServerI18n();

  return (
    <footer
      className="border-t py-8 text-center text-sm"
      style={{
        borderColor: "var(--card-border)",
        color: "var(--muted)",
      }}
    >
      <p>{dict.landing.footer}</p>
    </footer>
  );
}
