import Link from "next/link";

import { CreateCenterForm } from "@/components/centers/create-center-form";

export const metadata = {
  title: "Registrar centro de acopio · PrintForHelp",
};

export default function NewCenterPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href="/centers"
        className="text-sm text-muted hover:text-foreground"
      >
        ← Volver a centros de acopio
      </Link>

      <div className="mt-4 mb-8">
        <h1 className="text-2xl font-bold">Registrar centro de acopio</h1>
        <p className="mt-1 text-sm text-muted">
          Añade un punto de entrega para que la comunidad pueda llevar sus
          piezas impresas. No necesitas cuenta: un mantenedor lo revisará antes
          de marcarlo como verificado.
        </p>
      </div>

      <CreateCenterForm />
    </main>
  );
}
