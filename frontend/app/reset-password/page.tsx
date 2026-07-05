import { Alert, Card } from "@heroui/react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { getServerI18n } from "@/i18n/server";

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const user = await getCurrentUser();
  if (user) {
    redirect("/");
  }
  const { dict } = await getServerI18n();
  const { token } = await searchParams;

  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <Card.Header>
          <Card.Title>{dict.resetPassword.title}</Card.Title>
          <Card.Description>{dict.resetPassword.description}</Card.Description>
        </Card.Header>
        <Card.Content>
          {token ? (
            <ResetPasswordForm token={token} />
          ) : (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>
                  {dict.resetPassword.errorMissingToken}
                </Alert.Description>
              </Alert.Content>
            </Alert>
          )}
        </Card.Content>
        <Card.Footer>
          <Link
            href="/login"
            className="text-sm font-medium text-primary hover:underline"
          >
            {dict.resetPassword.backToLogin}
          </Link>
        </Card.Footer>
      </Card>
    </main>
  );
}
