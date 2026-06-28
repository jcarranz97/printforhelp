import { Card } from "@heroui/react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { RegisterForm } from "@/components/auth/register-form";
import { getServerI18n } from "@/i18n/server";

export default async function RegisterPage() {
  const user = await getCurrentUser();
  if (user) {
    redirect("/");
  }
  const { dict } = await getServerI18n();

  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <Card.Header>
          <Card.Title>{dict.register.title}</Card.Title>
          <Card.Description>{dict.register.description}</Card.Description>
        </Card.Header>
        <Card.Content>
          <RegisterForm />
        </Card.Content>
        <Card.Footer>
          <p className="text-sm text-muted">
            {dict.register.haveAccountPrompt}{" "}
            <Link
              href="/login"
              className="font-medium text-primary hover:underline"
            >
              {dict.register.loginLink}
            </Link>
          </p>
        </Card.Footer>
      </Card>
    </main>
  );
}
