import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { MyPrintsList } from "@/components/contributions/my-prints-list";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listCollectionCenters } from "@/lib/collection-centers.api";
import { listMyContributions } from "@/lib/contributions.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.myPrints.title} · PrintForHelp` };
}

export default async function MyPrintsPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/my-prints");
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value ?? "";
  const { dict } = await getServerI18n();
  const [contributions, centers] = await Promise.all([
    listMyContributions(token),
    listCollectionCenters({ verified: true }),
  ]);
  const centerOptions = centers
    .filter((center) => center.status === "active")
    .map((center) => ({ id: center.id, name: center.name }));

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-bold">{dict.myPrints.title}</h1>
      <p className="mt-1 mb-8 text-sm text-muted">{dict.myPrints.subtitle}</p>
      <MyPrintsList contributions={contributions} centers={centerOptions} />
    </main>
  );
}
