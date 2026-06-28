import { Card } from "@heroui/react";

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold">Sobre nosotros</h1>
      <p className="mt-4 text-lg text-muted">
        PrintForHelp es una plataforma comunitaria sin fines de lucro que
        conecta a quienes imprimen en 3D con quienes necesitan piezas de ayuda
        humanitaria.
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        <Card>
          <Card.Header>
            <Card.Title>Nuestra misión</Card.Title>
            <Card.Description>Coordinar ayuda, no duplicarla.</Card.Description>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">
              Centralizamos la información de centros de acopio, peticiones de
              piezas y producción en curso para que la comunidad cubra mejor la
              demanda y nadie imprima dos veces lo mismo.
            </p>
          </Card.Content>
        </Card>

        <Card>
          <Card.Header>
            <Card.Title>Enfoque inicial</Card.Title>
            <Card.Description>Férulas para Venezuela.</Card.Description>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted">
              Comenzamos coordinando la impresión de férulas médicas para las
              personas afectadas por el terremoto de junio de 2026 en Venezuela,
              con la mira puesta en convertirnos en un hub general de ayuda
              impresa en 3D.
            </p>
          </Card.Content>
        </Card>
      </div>

      <p className="mt-10 text-sm text-muted">
        ¿Quieres ayudar? Por ahora las cuentas las crea un administrador. Pronto
        habilitaremos el registro abierto para makers y organizaciones.
      </p>
    </main>
  );
}
