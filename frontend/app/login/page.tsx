import { Card } from "@heroui/react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { GoogleButton } from "@/components/auth/google-button";
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
        <Card.Content className="flex flex-col gap-5">
          <GoogleButton />
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="h-px flex-1 bg-default-200" />
            {dict.login.orDivider}
            <span className="h-px flex-1 bg-default-200" />
          </div>
          <LoginForm />
        </Card.Content>
        <Card.Footer>
          <p className="text-sm text-muted">
            {dict.login.noAccountPrompt}{" "}
            <Link
              href="/register"
              className="font-medium text-primary hover:underline"
            >
              {dict.login.registerLink}
            </Link>
          </p>
        </Card.Footer>
      </Card>
    </main>
  );
}
