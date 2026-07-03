# Flujo de trabajo para solicitudes de impresión 3D

## Inicio

### 1. Recepción de la solicitud

- Recibir la solicitud.
- Identificar:
  - ¿Qué problema se busca resolver?
  - ¿Quién solicita la ayuda?
  - ¿La necesidad ya fue verificada?

*Decisión:* ¿La necesidad está verificada?

- *No*
  - Solicitar información o validación adicional.
  - Esperar validación.
  - Regresar a la verificación.
- *Sí*
  - Continuar al siguiente paso.

---

### 2. Evaluar la viabilidad de impresión 3D

*Decisión:* ¿La impresión 3D es una solución adecuada?

- *No*
  - Buscar otra alternativa.
  - Cerrar la solicitud.
- *Sí*
  - Continuar.

---

### 3. Definir la solución

- Diseñar una nueva pieza *o*
- Seleccionar un diseño existente.
- Validar que la solución cumpla con la necesidad.

---

### 4. Definir los requerimientos de producción

Especificar:

- Tipo de pieza(s).
- Cantidad requerida.
- Material recomendado.
- Parámetros de impresión.
- ¿Requiere guía o instrucciones impresas?

---

### 5. Definir el alcance del proyecto

*Decisión:* ¿La producción puede realizarse con recursos locales?

#### Sí → Proyecto local

- La producción se asigna a makers del mismo país.
- La distribución se realiza localmente.

#### No → Solicitar apoyo internacional

El coordinador solicita apoyo a la comunidad internacional cuando:

- La capacidad de producción local es insuficiente.
- Fabricar en otro país reduce el tiempo de entrega.
- Fabricar en otro país reduce los costos.

---

### 6. Planificar la logística

Definir:

- Destinatario final.
- Dirección de entrega.
- Coordinador responsable.
- Método de envío.

---

### 7. Producción

- Asignar la fabricación.
- Confirmar la aceptación del trabajo por parte del maker.
- Dar seguimiento al proceso de fabricación.

---

### 8. Envío

*Decisión:* ¿Qué método de envío se usará?

Existen tres opciones. La **opción 3 es la preferida**; las
otras dos se usan cuando conviene por recursos, facilidad o urgencia.

#### Opción 3 (preferida) → Consolidación por el coordinador

- El maker envía las piezas al punto o dirección local que define el
  coordinador.
- El coordinador reúne todas las contribuciones.
- El coordinador envía todo junto al destino final.

#### Opción 1 → Envío directo del maker

- El maker envía su contribución directamente a la persona o lugar que
  la necesita (requiere la dirección específica del destinatario).
- Se usa cuando el contribuidor tiene los recursos o es fácil enviar
  directo.

#### Opción 2 → Entrega en centro de acopio

- El maker deja las piezas en un centro de acopio o lugar que puede
  hacer llegar la ayuda.
- Se usa en casos de emergencia, cuando hay un centro que puede
  entregar la ayuda con rapidez.

En cualquiera de las opciones:

- Preparar el envío.
- Registrar la información de seguimiento.
- Monitorear el transporte.

---

### 9. Confirmación de entrega

*Decisión:* ¿La entrega fue exitosa?

#### Sí

- Confirmar recepción con el destinatario.
- Documentar el resultado.
- Cerrar el proyecto.

#### No

- Identificar la incidencia.
- Definir acciones correctivas.
- Dar seguimiento hasta completar la entrega.

---

## Diagrama (Mermaid)

```mermaid
flowchart TD

    %% Nodo final compartido
    Z([Fin])

    %% =========================
    %% Recepción
    %% =========================
    subgraph A["Recepción y validación"]
        A1([Inicio])
        A2["Recepción de la solicitud<br/>• Identificar el problema<br/>• Identificar quién solicita la ayuda<br/>• Verificar la necesidad"]
        A3{"¿La necesidad está<br/>verificada?"}
        A4["Solicitar información<br/>o validación adicional"]

        A1 --> A2
        A2 --> A3
        A3 -->|No| A4
        A4 --> A3
    end

    %% =========================
    %% Diseño
    %% =========================
    subgraph B["Evaluación y diseño"]
        B1{"¿La impresión 3D es<br/>la solución adecuada?"}
        B2["Recomendar otra alternativa"]
        B3["Definir la solución<br/>• Diseñar una nueva pieza<br/>o seleccionar un diseño existente<br/>• Validar que resuelva la necesidad"]
        B4["Definir requerimientos<br/>de producción<br/><br/>• Tipo de pieza(s)<br/>• Cantidad<br/>• Material<br/>• Parámetros de impresión<br/>• ¿Incluye instrucciones impresas?"]

        B1 -->|No| B2
        B1 -->|Sí| B3
        B3 --> B4
    end

    %% =========================
    %% Producción
    %% =========================
    subgraph C["Planificación de la producción"]
        C1{"¿Puede producirse<br/>con recursos locales?"}
        C2["Proyecto local<br/>Asignar makers del mismo país"]
        C3["Solicitar apoyo internacional<br/>cuando:<br/>• No exista capacidad local<br/>• Se reduzca el tiempo<br/>• Se reduzca el costo"]
        C4["Planificar logística<br/>• Destinatario<br/>• Dirección<br/>• Coordinador<br/>• Método de envío"]

        C1 -->|Sí| C2
        C1 -->|No| C3
        C2 --> C4
        C3 --> C4
    end

    %% =========================
    %% Ejecución
    %% =========================
    subgraph D["Producción y entrega"]
        D1["Asignar producción<br/>• Confirmar aceptación del maker"]
        D2["Fabricación"]
        DE{"¿Qué método<br/>de envío?"}

        S3["Opción 3 (preferida)<br/>Consolidación por el coordinador<br/>• El maker envía al punto local<br/>que define el coordinador<br/>• El coordinador reúne todas las piezas<br/>• Envía todo junto al destino"]
        S1["Opción 1<br/>Envío directo del maker<br/>Al destinatario final<br/>(requiere dirección específica)"]
        S2["Opción 2<br/>Entrega en centro de acopio<br/>Un centro hace llegar la ayuda<br/>(útil en emergencias)"]

        D3["Preparar envío<br/>• Registrar guía<br/>• Dar seguimiento"]
        D4{"¿Entrega<br/>confirmada?"}
        D5["Resolver incidencia"]
        D6["Documentar resultados<br/>y cerrar proyecto"]

        D1 --> D2
        D2 --> DE
        DE -->|Preferida| S3
        DE -->|Si hay recursos o es fácil| S1
        DE -->|Emergencia| S2
        S3 --> D3
        S1 --> D3
        S2 --> D3
        D3 --> D4
        D4 -->|No| D5
        D5 --> D3
        D4 -->|Sí| D6
    end

    %% =========================
    %% Conexiones entre etapas
    %% =========================
    A3 -->|Sí| B1
    B2 --> Z
    B4 --> C1
    C4 --> D1
    D6 --> Z
```
