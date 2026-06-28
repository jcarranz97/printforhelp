import { FaDiscord, FaGithub } from "react-icons/fa";

import { getServerI18n } from "@/i18n/server";
import { DISCORD_URL, GITHUB_URL } from "@/lib/links";

/**
 * Global site footer shown on every page. Server component so it can read
 * the active locale dictionary directly. Includes the GitHub and Discord
 * community links.
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
      <div className="flex items-center justify-center gap-5">
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          aria-label={dict.social.githubAriaLabel}
          className="transition-colors hover:text-foreground"
        >
          <FaGithub className="h-5 w-5" />
        </a>
        <a
          href={DISCORD_URL}
          target="_blank"
          rel="noreferrer"
          aria-label={dict.social.discordAriaLabel}
          className="transition-colors hover:text-foreground"
        >
          <FaDiscord className="h-5 w-5" />
        </a>
      </div>
      <p className="mt-4">{dict.landing.footer}</p>
    </footer>
  );
}
