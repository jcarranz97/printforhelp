import { Card } from "@heroui/react";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { LoginForm } from "@/components/auth/login-form";

export default async function LoginPage() {
  const user = await getCurrentUser();
  if (user) {
    redirect("/");
  }

  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <Card.Header>
          <Card.Title>Iniciar sesión</Card.Title>
          <Card.Description>
            Inicia sesión para coordinar la ayuda.
          </Card.Description>
        </Card.Header>
        <Card.Content>
          <LoginForm />
        </Card.Content>
        <Card.Footer>
          <p className="text-xs text-muted">
            Por ahora no admitimos el registro de nuevos usuarios. ¡Mantente
            atento, pronto habilitaremos esta opción!
          </p>
        </Card.Footer>
      </Card>
    </main>
  );
}
