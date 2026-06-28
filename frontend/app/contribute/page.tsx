import { Card } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import { FaCode, FaDiscord, FaGithub } from "react-icons/fa";

import { getServerI18n } from "@/i18n/server";
import {
  API_BASE_URL,
  API_DOCS_URL,
  DISCORD_URL,
  GITHUB_ISSUES_URL,
  GITHUB_URL,
} from "@/lib/links";

/** Strip the scheme so the link text reads as a bare host/path. */
function displayUrl(url: string): string {
  return url.replace(/^https?:\/\//, "");
}

/**
 * Render a translated string that contains `{apiUrl}` / `{docsUrl}` tokens,
 * replacing each token with a real anchor while keeping the surrounding copy
 * intact in whichever language is active.
 */
function withApiLinks(template: string) {
  return template.split(/(\{apiUrl\}|\{docsUrl\})/g).map((part, index) => {
    const href =
      part === "{apiUrl}"
        ? API_BASE_URL
        : part === "{docsUrl}"
          ? API_DOCS_URL
          : null;
    if (!href) {
      return part;
    }
    return (
      <a
        key={index}
        href={href}
        target="_blank"
        rel="noreferrer"
        className="font-medium underline"
        style={{ color: "var(--accent-strong)" }}
      >
        {displayUrl(href)}
      </a>
    );
  });
}

export default async function ContributePage() {
  const { dict } = await getServerI18n();
  const t = dict.contribute;

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-4 text-lg text-muted">{t.intro}</p>

      <div className="mt-10 grid gap-6">
        <Card>
          <Card.Header>
            <Card.Title>{t.repoTitle}</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">{t.repoBody}</p>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className={`${buttonVariants({ size: "sm" })} mt-4 inline-flex items-center gap-2`}
            >
              <FaGithub aria-hidden className="h-4 w-4" />
              {t.repoCta}
            </a>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header>
            <Card.Title>{t.apiTitle}</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">{withApiLinks(t.apiBody)}</p>
            <a
              href={API_DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className={`${buttonVariants({ size: "sm" })} mt-4 inline-flex items-center gap-2`}
            >
              <FaCode aria-hidden className="h-4 w-4" />
              {t.apiCta}
            </a>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header>
            <Card.Title>{t.issuesTitle}</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">{t.issuesBody}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <a
                href={GITHUB_ISSUES_URL}
                target="_blank"
                rel="noreferrer"
                className={`${buttonVariants({ size: "sm" })} inline-flex items-center gap-2`}
              >
                <FaGithub aria-hidden className="h-4 w-4" />
                {t.issuesCta}
              </a>
              <a
                href={DISCORD_URL}
                target="_blank"
                rel="noreferrer"
                className={`${buttonVariants({ size: "sm", variant: "secondary" })} inline-flex items-center gap-2`}
              >
                <FaDiscord aria-hidden className="h-4 w-4" />
                {t.issuesDiscordCta}
              </a>
            </div>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header>
            <Card.Title>{t.discordTitle}</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">{t.discordBody}</p>
            <a
              href={DISCORD_URL}
              target="_blank"
              rel="noreferrer"
              className={`${buttonVariants({ size: "sm" })} mt-4 inline-flex items-center gap-2`}
            >
              <FaDiscord aria-hidden className="h-4 w-4" />
              {t.discordCta}
            </a>
          </Card.Content>
        </Card>
      </div>
    </main>
  );
}
