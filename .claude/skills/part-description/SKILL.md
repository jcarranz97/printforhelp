---
name: part-description
description: Generate a bilingual (English + Spanish) Markdown description for a single PrintForHelp printable part (a 3D-printed splint/ferula or other relief part). Use when the user provides a part name, a designer/creator, print instructions, and/or links (Instagram, MakerWorld, Google Drive) and wants a clean .md file with an English and a Spanish version ready to copy-paste into the part page.
---

# Part Description Generator

Turn raw notes about a single printable part (a name, who designed it,
how to print it, links, a label) into a polished, bilingual Markdown file
the user can paste directly into a PrintForHelp part page.

## When to use

The user describes **one printable part** and asks for a `.md` file with
English and Spanish versions. Input may be a part name, a screenshot or
text of fabrication instructions, a designer's social handle, a MakerWorld
URL, a Google Drive link, and/or a label image. It may be in Spanish only,
English only, or both.

A **part description** is different from a **request description** (a
campaign/need) and a **center description** (drop-off points). A part
description is for one printable file.

## Output format

Write a single `.md` file with **English first, Spanish second**, separated
by a `---` horizontal rule. Each language block uses the same structure so
the two are mirror translations of each other.

Section order (omit a section only when it does not apply):

1. **Title** `### <emoji> <part name>` (use a placeholder
   `[PART NAME]` / `[NOMBRE DE LA PIEZA]` if the name is unknown).
2. **Intro paragraph** — what the part is (a 3D-printed medical splint
   /férula, a pet splint, etc.), who designed it, and the relief context.
   ALWAYS credit the designer/creator here.
3. **Source / resource links** (when given): MakerWorld 🔗, Google Drive
   📁 (note what is inside, e.g. .3mf files and label PDFs), Instagram 📸,
   designer profile 👤.
4. **Sizes** 📏 (when given) — list each size and who it fits.
5. **Materials needed** 🧰 (when given, e.g. Velcro).
6. **How to print it** 🖨️ — material, walls, infill, supports,
   orientation, and any special notes. Use a bulleted list.
7. **About thermoforming** 🔥 — INCLUDE ONLY for thermoformable splints
   (the LayerLab / Ostec3d ferulas). Skip it for parts that are not
   thermoformed (e.g. Velcro-fitted braces, flexible prints).
8. **Latest version** 🔄 (when the user mentions a changelog/version).
9. **Label for this part** 🏷️ — see the label rule below.
10. **Credits** 💜 — designer/creator, links, and (for MakerWorld designs)
    a line asking people to post comments/improvements directly on the
    MakerWorld page so they reach the designer.
11. **Closing call-to-action** in bold, ending with 💚.

## Rules

- **Bilingual, English on top, Spanish on the bottom.** Both versions must
  carry the same information and structure.
- **ALWAYS include the designer/creator.** Credit them in the intro and in
  the Credits section, with whatever links the user provides (Instagram
  handle as `[@handle](url)`, MakerWorld profile, etc.). If the uploader
  and the designer differ, name both and flag it to the user afterward.
- **If the user provides the designer's social URL, always include it** as
  a clickable link in both the intro and the Credits section (e.g. render
  the handle as `**@handle** ([Instagram](<url>))`). Use the full URL
  exactly as given, including any tracking parameters. Keep the same link
  in both language blocks.
- **Translate print instructions faithfully.** Keep numeric values exactly
  as given (infill %, wall loops, support threshold angle, scale %). Do
  not invent settings the user did not provide.
- **Common term translations**: relleno = infill, paredes/wall loops =
  walls, soportes = supports, soportes tipo árbol = tree supports,
  escala = scale, termoformable = thermoformable.
- **Label section** — ALWAYS ask the user whether this part has a label to
  print, unless they already made it clear. Then:
  - If the user gives a label image URL, embed it with
    `![Label for this part](URL)` / `![Etiqueta para esta pieza](URL)`.
  - If the user says there is a label but has not uploaded it yet, use a
    placeholder URL `[LABEL IMAGE URL PLACEHOLDER]` /
    `[URL DE LA IMAGEN DE LA ETIQUETA]`.
  - If the user says the part has NO label, replace the section body with
    a short note: "There is no label provided for this part. Just print
    the piece and drop it off at a collection center." / "No hay etiqueta
    disponible para esta pieza. Solo imprime la pieza y entrégala en un
    centro de acopio."
- **Preserve the user's emojis** and use the section emojis above
  consistently in both languages.
- **Preserve lists as Markdown lists** (`- item`). Convert inline bullets
  (•, etc.) into `-`.
- **Bold the closing call-to-action** in both languages, e.g. "Thank you
  for printing and helping. We are counting on your solidarity!" /
  "Gracias por imprimir y ayudar. ¡Contamos con tu solidaridad!".
- **No em dashes (—)** anywhere in the copy. Reword with commas or colons.
  This is a standing user preference.
- Keep proper nouns (part names, designer handles, brand names) as given;
  do not translate them. Translate descriptive headings for each block.
- If input is Spanish-only, translate naturally into English; if
  English-only, translate naturally into Spanish.

## Where to save

**Save to `part-description.md` at the repo root** by default. When the
user is building several part descriptions (the common case), save to
`part-description-<slug>.md` instead (e.g.
`part-description-neck-splint.md`, `part-description-lucamorbe.md`) so the
files coexist. Pick a slug from the part name or the designer; if unclear,
ask or default to the designer handle.

## After writing

Tell the user the filename and give a one-line summary. Flag any inferred
names, part type, settings, or attribution (designer vs. uploader) so they
can correct them, and call out any placeholders they still need to fill
(part name, label image URL).

## Reference example (LayerLab / Ostec3d ferula, the generic template)

```markdown
## 🌎 English

### 🦾 [PART NAME]

This part is a **3D-printed medical splint (férula)** for earthquake
relief in Venezuela. It is part of the designs generously shared by the
Venezuelan 3D printing teams **LayerLab**
([@somoslayerlab](https://www.instagram.com/somoslayerlab)) and
**Ostec3d** ([@ostec3d](https://www.instagram.com/ostec3d)) so any maker
can reproduce it from home and help people who need care for fractures
and injuries.

### 🖨️ How to print it

- 🧵 Print in **PLA filament**.
- ✅ Print the part as shown in the photo.
- 📦 Once printed, it is ready to be dropped off at a collection center.

### 🔥 About thermoforming (termoformado)

These splints use a technique called **thermoforming**: the printed part
is gently heated and then shaped and fitted directly onto the patient
where it is needed. The medical team handles this final step, so you do
not need to do anything beyond printing the piece.

### 🏷️ Label for this part

Each printed piece must be shipped together with its **printed label**.
Please print the label below, attach it to the piece, and include it in
the package:

![Label for this part]([LABEL IMAGE URL PLACEHOLDER])

### 💜 Credits

Design shared by **LayerLab** and **Ostec3d**. Please follow them for
updates and fitting guidance. Every férula counts.

**Thank you for printing and helping. We are counting on your
solidarity!** 💚

---

## 🌎 Español

### 🦾 [NOMBRE DE LA PIEZA]

Esta pieza es una **férula médica impresa en 3D** para la ayuda tras los
terremotos en Venezuela. Forma parte de los diseños compartidos
generosamente por los equipos venezolanos de impresión 3D **LayerLab**
([@somoslayerlab](https://www.instagram.com/somoslayerlab)) y **Ostec3d**
([@ostec3d](https://www.instagram.com/ostec3d)), para que cualquier maker
pueda reproducirla desde casa y ayudar a quienes necesitan atención por
fracturas y lesiones.

### 🖨️ Cómo imprimirla

- 🧵 Imprime en **filamento PLA**.
- ✅ Imprime la pieza tal como se muestra en la foto.
- 📦 Una vez impresa, está lista para entregarse en un centro de acopio.

### 🔥 Sobre el termoformado

Estas férulas usan una técnica llamada **termoformado**: la pieza impresa
se calienta con cuidado y luego se moldea y se coloca directamente sobre
el paciente donde se necesita. El equipo médico se encarga de este último
paso, así que no necesitas hacer nada más que imprimir la pieza.

### 🏷️ Etiqueta para esta pieza

Cada pieza impresa debe enviarse junto con su **etiqueta impresa**. Por
favor imprime la etiqueta de abajo, pégala a la pieza e inclúyela en el
paquete:

![Etiqueta para esta pieza]([URL DE LA IMAGEN DE LA ETIQUETA])

### 💜 Créditos

Diseño compartido por **LayerLab** y **Ostec3d**. Por favor síguelos para
ver actualizaciones e indicaciones de colocación. Cada férula cuenta.

**Gracias por imprimir y ayudar. ¡Contamos con tu solidaridad!** 💚
```
