import { Card } from "@heroui/react";

import { getServerI18n } from "@/i18n/server";

export default async function AboutPage() {
  const { dict } = await getServerI18n();
  const t = dict.about;

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-4 text-lg text-muted">{t.intro}</p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        <Card>
          <Card.Header>
            <Card.Title>{t.missionTitle}</Card.Title>
            <Card.Description>{t.missionTagline}</Card.Description>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">{t.missionBody}</p>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header>
            <Card.Title>{t.focusTitle}</Card.Title>
            <Card.Description>{t.focusTagline}</Card.Description>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">{t.focusBody}</p>
          </Card.Content>
        </Card>
      </div>

      <p className="mt-10 text-sm text-muted">{t.helpNote}</p>
    </main>
  );
}
