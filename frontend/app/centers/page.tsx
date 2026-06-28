import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { cookies } from "next/headers";

import { getCurrentUser } from "@/actions/auth.action";
import { CentersDirectory } from "@/components/centers/centers-directory";
import { UnverifiedCenters } from "@/components/centers/unverified-centers";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listCollectionCenters } from "@/lib/collection-centers.api";

export const metadata = {
  title: "Centros de acopio · PrintForHelp",
  description:
    "Directorio público de centros de acopio donde entregar tus piezas impresas en 3D.",
};

export default async function CentersPage() {
  const user = await getCurrentUser();
  const token = user
    ? (await cookies()).get(AUTH_COOKIE_NAME)?.value
    : undefined;
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";

  // The public directory includes unverified centers (badged "No
  // verificado"). Maintainers additionally get a focused review queue of
  // the unverified ones with one-click verification.
  const centers = await listCollectionCenters();
  const unverified =
    isMaintainer && token
      ? await listCollectionCenters({ verified: false }, token)
      : [];

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Centros de acopio</h1>
          <p className="mt-1 text-sm text-muted">
            Puntos de entrega donde llevar tus piezas impresas para que lleguen
            a quien las necesita.
          </p>
        </div>
        <Link href="/centers/new" className={buttonVariants({ size: "sm" })}>
          Registrar centro
        </Link>
      </div>

      <CentersDirectory centers={centers} />

      {isMaintainer && unverified.length > 0 && (
        <UnverifiedCenters centers={unverified} />
      )}
    </main>
  );
}
