import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      <section className="mx-auto max-w-5xl px-6 pt-24 pb-16 text-center">
        <p
          className="text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--accent)" }}
        >
          Comunidad 3D
        </p>
        <h1 className="mt-4 text-5xl font-bold leading-tight sm:text-6xl">
          PrintForHelp
        </h1>
        <p
          className="mx-auto mt-6 max-w-2xl text-lg sm:text-xl"
          style={{ color: "var(--muted)" }}
        >
          Conectamos a quienes imprimen en 3D con quienes necesitan piezas —
          empezando por férulas para los afectados por el terremoto en
          Venezuela.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <a
            href="#features"
            className="rounded-full px-6 py-3 font-medium text-white transition-opacity hover:opacity-90"
            style={{ background: "var(--accent-strong)" }}
          >
            ¿Cómo funciona?
          </a>
          <button
            type="button"
            className="rounded-full border px-6 py-3 font-medium transition-colors hover:bg-black/5"
            style={{
              borderColor: "var(--card-border)",
              color: "var(--foreground)",
            }}
          >
            Quiero ayudar
          </button>
        </div>
      </section>

      <section
        id="features"
        className="mx-auto max-w-5xl px-6 pt-8 pb-24"
        aria-label="Funciones principales"
      >
        <div className="grid gap-6 sm:grid-cols-3">
          <FeatureCard
            title="Centros de acopio"
            description="Directorio de puntos de entrega donde llevar tus piezas impresas para que lleguen a quien las necesita."
            href="/centers"
          />
          <FeatureCard
            title="Peticiones de piezas"
            description="Quien necesita una férula u otra pieza puede solicitarla aquí, con detalles y urgencia."
            badge="Próximamente"
          />
          <FeatureCard
            title="¿Qué estás imprimiendo?"
            description="Reporta lo que tienes en cola para que la comunidad no duplique trabajo y cubra mejor la demanda."
            badge="Próximamente"
          />
        </div>
      </section>

      <footer
        className="border-t py-8 text-center text-sm"
        style={{
          borderColor: "var(--card-border)",
          color: "var(--muted)",
        }}
      >
        <p>
          PrintForHelp · Proyecto comunitario sin fines de lucro · MIT License
        </p>
      </footer>
    </main>
  );
}

type FeatureCardProps = {
  title: string;
  description: string;
  badge?: string;
  href?: string;
};

function FeatureCard({ title, description, badge, href }: FeatureCardProps) {
  const card = (
    <div
      className="h-full rounded-2xl border p-6 transition-shadow hover:shadow-md"
      style={{
        background: "var(--card)",
        borderColor: "var(--card-border)",
      }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{title}</h3>
        {badge && (
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              background: "color-mix(in srgb, var(--accent) 12%, transparent)",
              color: "var(--accent-strong)",
            }}
          >
            {badge}
          </span>
        )}
      </div>
      <p className="mt-3 text-sm" style={{ color: "var(--muted)" }}>
        {description}
      </p>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {card}
      </Link>
    );
  }
  return card;
}
