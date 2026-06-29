---
name: new-part-message
description: Generate a bilingual (Spanish + English) WhatsApp announcement that a new printable part is now live on PrintForHelp. Use when the user provides a PrintForHelp part URL (https://printforhelp.org/parts/<id>) and wants a ready-to-paste plain-text message for WhatsApp/social groups. The only input needed is the part URL.
---

# New Part Communication Message

Turn a single PrintForHelp part URL into a short, warm, ready-to-paste
WhatsApp announcement that a new part is available, in Spanish and English.

## When to use

The user has just posted a new part on PrintForHelp and gives you the part
URL (e.g. `https://printforhelp.org/parts/9f55717c-...`). They want a
plain-text message they can paste into WhatsApp or social groups to let
the community know there is a new part to print and to ask people to share
it. **The only required input is the URL.**

## Steps

### 1. Read the part page

Fetch the URL with WebFetch and extract:

- The **part name** (as shown on the page).
- The **designer/creator** (e.g. an Instagram handle like `@lucamorbe`, or
  teams like LayerLab / Ostec3d).
- A **one-line sense of what the part is** (a medical splint/ferula, a pet
  splint, a neck stabilizer, etc.).

If the page cannot be read (private/blocked), ask the user to paste the
part name and designer, then continue. Do not invent details.

### 2. Draft the message

Write a short announcement following the structure below, one for each
language. Keep it warm and brief. The two languages are saved to two
separate files (see "Where to save").

Structure (per language):

```
<themed emoji> *New part available!* <themed emoji>

We added <part name> to our page, <one short line on what it is and who
it helps>. <credit the designer/creator>. 💚

You can access the part directly on PrintForHelp, where everything is:
the printing instructions, the sizes, and the resources/credits. 🖨️

👉 <part URL>

🙏 If you can, *share the link* so more people join in.
*We are counting on your solidarity!* 💜
```

Pick a themed emoji that matches the part (🦵 leg, 🦾 arm, 🦴 splint, 🐾
pet, etc.). Use the part name exactly as it appears on the page (you may
add proper Spanish accents in the Spanish block).

### 3. Output format

- **Plain text, not Markdown** (WhatsApp does not render Markdown). Use
  WhatsApp formatting only: `*bold*` with single asterisks, plus emojis.
- **Two separate files**: one for Spanish, one for English (see "Where to
  save"). Do not combine them or add a divider line; each file holds only
  its own language.
- Start each file with its flag header (`🇪🇸 ESPAÑOL` / `🇬🇧 ENGLISH`).
- **No em dashes (—)** anywhere. Reword with commas or colons. Standing
  user preference.
- Keep it short: a few lines per language. This is a chat message, not a
  full description.
- Always include the part URL on its own line, prefixed with `👉`.
- Always end each block with the bold call-to-action and 💜.

## Where to save

Save **two** plain-text files at the repo root, where `<slug>` is derived
from the part name (e.g. `ferula-pierna-v2`):

- Spanish → `whatsapp-<slug>-es.txt`
- English → `whatsapp-<slug>-en.txt`

Overwrite if they already exist.

## After writing

Tell the user both filenames and give a one-line summary. Flag anything you
inferred (such as adding accents to the part name) so they can correct it.

## Reference example

Input: `https://printforhelp.org/parts/9f55717c-acf9-469e-b5da-ac20cc6bc0c0`
(part page shows "Ferula Pierna V2" by @lucamorbe)

Output file 1 (`whatsapp-ferula-pierna-v2-es.txt`):

```
🇪🇸 ESPAÑOL

🦵 *¡Nueva pieza disponible!* 🦵

Agregamos a nuestra página la *Férula de Pierna V2*, una férula impresa
en 3D para ayudar a quienes necesitan atención por fracturas en
Venezuela. 💚

Puedes acceder directamente a la pieza en PrintForHelp, donde está todo:
las instrucciones de impresión, las tallas y los créditos del diseñador
(@lucamorbe). 🖨️

👉 https://printforhelp.org/parts/9f55717c-acf9-469e-b5da-ac20cc6bc0c0

🙏 Si puedes, *comparte el enlace* para que más personas se sumen.
*¡Contamos con tu solidaridad!* 💜
```

Output file 2 (`whatsapp-ferula-pierna-v2-en.txt`):

```
🇬🇧 ENGLISH

🦵 *New part available!* 🦵

We added the *Ferula Pierna V2* (leg splint) to our page, a 3D-printed
splint to help people who need care for fractures in Venezuela. 💚

You can access the part directly on PrintForHelp, where everything is: the
printing instructions, the sizes, and the designer's credits
(@lucamorbe). 🖨️

👉 https://printforhelp.org/parts/9f55717c-acf9-469e-b5da-ac20cc6bc0c0

🙏 If you can, *share the link* so more people join in.
*We are counting on your solidarity!* 💜
```
