import { Card } from "@heroui/react";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { LoginForm } from "@/components/auth/login-form";
import { getServerI18n } from "@/i18n/server";

export default async function LoginPage() {
  const user = await getCurrentUser();
  if (user) {
    redirect("/");
  }
  const { dict } = await getServerI18n();

  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <Card.Header>
          <Card.Title>{dict.login.title}</Card.Title>
          <Card.Description>{dict.login.description}</Card.Description>
        </Card.Header>
        <Card.Content>
          <LoginForm />
        </Card.Content>
        <Card.Footer>
          <p className="text-xs text-muted">{dict.login.footerNote}</p>
        </Card.Footer>
      </Card>
    </main>
  );
}
