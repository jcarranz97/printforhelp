import { Card } from "@heroui/react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { getServerI18n } from "@/i18n/server";

export default async function ForgotPasswordPage() {
  const user = await getCurrentUser();
  if (user) {
    redirect("/");
  }
  const { dict } = await getServerI18n();

  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <Card.Header>
          <Card.Title>{dict.forgotPassword.title}</Card.Title>
          <Card.Description>{dict.forgotPassword.description}</Card.Description>
        </Card.Header>
        <Card.Content>
          <ForgotPasswordForm />
        </Card.Content>
        <Card.Footer>
          <Link
            href="/login"
            className="text-sm font-medium text-primary hover:underline"
          >
            {dict.forgotPassword.backToLogin}
          </Link>
        </Card.Footer>
      </Card>
    </main>
  );
}
