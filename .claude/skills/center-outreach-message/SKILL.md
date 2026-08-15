---
name: center-outreach-message
description: Generate a short Spanish WhatsApp first-contact message to a potential PrintForHelp partner (a veterinary clinic, Red Cross chapter, hospital, foundation or collection center) asking whether they need 3D-printed aid and offering to connect them with makers. Use when the user names a center and what it might need (pet splints, human splints, other relief parts) and wants a ready-to-paste message to send to that center's phone number.
---

# Center Outreach Message

Turn "the center is X, they might need Y" into a short, warm, ready-to-paste
Spanish WhatsApp message for a **cold first contact** with that center.

## When to use

The user is reaching out to many potential partners one by one: veterinary
clinics that may need pet leg splints, Red Cross chapters / hospitals /
foundations that may need human splints, shelters, collection centers, etc.
They give the center's name and what it might need, and want the message
text to paste into WhatsApp.

**Spanish only** unless the user explicitly asks for English too.

## Inputs

Required (ask only for what is missing, in one short question):

- **Center name** (e.g. "Hospital Público Veterinario").
- **What they might need** (e.g. "férulas para mascotas", "férulas para
  personas", "inmovilizadores").
- **City** (e.g. Pereira), used for the delivery line.

Optional, use if given:

- **How we heard about them** ("un médico nos comentó", "vimos su página",
  "nos recomendó la Cruz Roja"). Defaults to a neutral phrasing if absent.
- **Contact person's name** ("Hola, doctora Ana").
- **Whether the part is already published** on PrintForHelp, and its link.
- A **different sender name**. Default sender is **Juan Carranza**.

Never invent a referral source, a part link, quantities or dates. If the
user did not say it, leave it out.

## Message structure

Five short blocks, one blank line between each (WhatsApp reads better this
way):

1. **Saludo.** `Hola, buenas 👋` (or `Hola, doctor(a) <nombre>, buenas 👋`).
2. **Quién soy y qué es PrintForHelp.** Name, "les escribo de parte de
   PrintForHelp (printforhelp.org), una iniciativa sin ánimo de lucro que
   conecta a personas con impresoras 3D con quienes necesitan piezas de
   ayuda."
3. **La razón del contacto, terminada en pregunta.** Say how we heard of
   them (if known) and what we believe they need, then `¿Es correcto?`.
   Asking beats asserting: it is a cold message and the premise may be
   wrong.
4. **La propuesta concreta.** What happens if they say yes: makers in the
   area print the part, and deliveries go directly to their address in
   `<ciudad>`. Close with `¿Les serviría así?`.
5. **Cierre.** `Quedo atento a su respuesta. ¡Muchas gracias! 🙏`

## Tone and style rules

- **Usted**, never tú. These are institutions.
- **Short.** Around 6 to 10 lines total. It is a cold WhatsApp message; a
  wall of text does not get read.
- Warm and plain. No marketing language, no "revolucionamos", no bullet
  lists, no bold headers.
- **Adapt the vocabulary to the recipient**: a veterinary clinic gets
  "férulas para mascotas" and "los peluditos que llegan lesionados"; a Red
  Cross chapter or hospital gets "férulas para personas" / "para pacientes
  con fracturas". Never mix the two audiences in one message.
- **Never promise** amounts, deadlines, or that makers are already
  committed. The offer is to try to connect them, nothing more.
- **No em dashes (—)** anywhere. Reword with commas or colons. Standing
  user preference.
- Plain text, not Markdown (WhatsApp does not render it). WhatsApp
  formatting only: `*bold*` with single asterisks, plus a few emojis. Use
  emojis sparingly here: this is a professional first contact, not a
  community announcement.
- If the part is already published, say `ya tenemos la pieza publicada` and
  include the link on its own line. Otherwise say `publicaríamos la pieza`.

## Where to save

Save one plain-text file at the repo root:

`mensaje-contacto-<slug>.txt`

where `<slug>` comes from the center name and city (e.g.
`hospital-veterinario-pereira`, `cruz-roja-pereira`). Overwrite if it
already exists. The file holds only the message, with no header line, so it
can be copied whole.

## After writing

Tell the user the filename, then flag in one or two lines anything you
assumed or left out (a referral source you kept vague, a link you did not
have). Offer the swap between `publicaríamos la pieza` and `ya tenemos la
pieza publicada` if you had to guess.

## Reference example

Input: "Hospital Público Veterinario en Pereira, férulas para mascotas, nos
lo comentó un médico, la pieza aún no está publicada."

Output file (`mensaje-contacto-hospital-veterinario-pereira.txt`):

```text
Hola, buenas 👋

Mi nombre es Juan Carranza y les escribo de parte de PrintForHelp
(printforhelp.org), una iniciativa sin ánimo de lucro que conecta a
personas con impresoras 3D con quienes necesitan piezas de ayuda.

Un médico nos comentó que ustedes podrían tener necesidad de férulas
para mascotas. ¿Es correcto?

Si es así, publicaríamos la pieza para que los makers de la zona puedan
imprimirla, y las entregas se harían directamente en su dirección en
Pereira. ¿Les serviría así?

Quedo atento a su respuesta. ¡Muchas gracias! 🙏
```

Same input but for a Red Cross chapter needing human splints, block 3 and 4
become:

```text
Vimos que ustedes atienden a personas con fracturas y quisimos
preguntarles si tendrían necesidad de férulas impresas en 3D. ¿Es
correcto?

Si es así, publicaríamos la pieza para que los makers de la zona puedan
imprimirla, y las entregas se harían directamente en su sede en Pereira.
¿Les serviría así?
```
