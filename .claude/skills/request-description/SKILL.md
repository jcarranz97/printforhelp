---
name: request-description
description: Generate a bilingual (English + Spanish) Markdown description for a PrintForHelp request (a campaign/need, e.g. "Splints for Hogar Bambi"). Use when the user provides details about a need, a charity/hospital/organization, a point of contact, or a WhatsApp/message excerpt and wants a clean .md file with an English and a Spanish version ready to copy-paste into the request page.
---

# Request Description Generator

Turn raw notes about a need (a forwarded WhatsApp message, a quick
description of a charity, a point of contact, some links) into a polished,
bilingual Markdown file the user can paste directly into a PrintForHelp
request page.

## When to use

The user describes a **request** (a campaign-level need: who needs help,
what they need, and who is coordinating it) and asks for a `.md` file with
English and Spanish versions. Input may arrive as a forwarded message,
a short paragraph, a charity name plus links, or a mix. It may be in
Spanish only, English only, or both.

A **request** is different from a **center description** (drop-off points)
and a **part description** (a single printable file). A request is the
"why we are printing" campaign, usually tied to an organization, hospital,
or charity, and a point of contact who makes sure the parts reach the
people in need.

## Output format

Write a single `.md` file with **English first, Spanish second**, separated
by a `---` horizontal rule. Each language block uses the same structure so
the two are mirror translations of each other.

Template:

```markdown
## 🌎 English

### <emoji> <short request title>

<1-2 sentence summary of the need and its urgency.>

<Paragraph: who they are (charity/hospital/org), what they told us, and
how big the need is. Translate naturally, do not copy word-for-word.>

<optional reference links block: website, Google Maps, social media>

<optional: a line about what this means for makers, e.g. there is still a
lot to print, every part counts.>

🤝 **Point of contact:** <name>. <What they are doing to coordinate and
make sure the printed parts reach the people who need them.>

🙏 <A short call to join in. If the specifics are still being confirmed,
say the request will be kept updated.>

**<bold closing call-to-action>** 💚

---

## 🌎 Español

### <emoji> <short request title in Spanish>

<mirror translation of everything above>

**<bold closing call-to-action in Spanish>** 💚
```

## Rules

- **Bilingual, English on top, Spanish on the bottom.** Both versions must
  carry the same information and structure.
- **Lead with the need and its urgency**, then who the organization is,
  then who is coordinating it.
- **Always include a "Point of contact" line** when the user names one.
  State what that person is doing to make sure the help reaches the people
  in need (e.g. in direct contact with the charity, confirming exact
  needs with a hospital).
- **Add reference links as a tidy block** when given (website 🌐, Google
  Maps 📍, Instagram/social 📸/📲). Use Markdown links with a short label;
  keep the same links in both language blocks.
- **Do NOT include private contact details** (phone numbers, personal
  addresses) by default. A request page is public. If the user explicitly
  says to include a phone/email/handle, add it; otherwise just use the
  person's first name.
- **Preserve the user's emojis** and place them consistently in both
  languages. If the input has none, add a few tasteful ones (not on every
  line) in a warm tone.
- **Preserve lists as Markdown lists** (`- item`) when the input lists
  specific items or steps. Convert inline bullets (•, etc.) into `-`.
- **Bold the closing call-to-action** (e.g. "Thank you for helping. We are
  counting on your solidarity!" / "Gracias por ayudar. ¡Contamos con tu
  solidaridad!") in both languages.
- **No em dashes (—)** anywhere in the copy. Reword with commas or colons.
  This is a standing user preference.
- Keep section headings short. If the user gave a title or charity name,
  reuse it (translate the heading for the English block; keep proper nouns
  like "Hogar Bambi" untranslated).
- If input is Spanish-only, translate naturally into English (not
  word-for-word). If English-only, translate naturally into Spanish.
- **Quote sources faithfully but clean them up.** When summarizing a
  forwarded message, capture what was said without inventing facts. If
  something is still uncertain (e.g. exact quantities not yet known), say
  it is being confirmed rather than guessing numbers.

## Where to save

**Save to `request-description.md` at the repo root** by default,
overwriting the existing file. If the request is for a specific named
organization and the user is building several, you may instead save to
`request-description-<slug>.md` (e.g. `request-description-hogar-bambi.md`)
so multiple requests can coexist. When in doubt, ask which name to use, or
default to the plain `request-description.md`.

## After writing

Tell the user the filename and give a one-line summary of what you
produced. Flag any names, spellings, links, or ambiguous terms you had to
infer so they can correct them. Explicitly note anything you deliberately
left out (such as a phone number) so they can add it back if they want.

## Reference example

Input (forwarded WhatsApp message, English):

```
Hi guys! I just spoke to one of the organizers of Hogar Bambi, a
children's charity in Venezuela. She tells me the need for splints is
through the roof. The amount of kids with broken bones is massive and
they're going to need as many as they can get. She's getting me in
contact with a children's hospital to see exactly what they need.

Point of contact: Pati. Website: https://hogarbambi.org/
```

Output file (`request-description-hogar-bambi.md`):

```markdown
## 🌎 English

### 🦴 Splints needed for Hogar Bambi (children in Venezuela)

The need for splints is still huge. 💔

We connected with one of the organizers of **Hogar Bambi**, a children's
charity in Venezuela. She tells us the need for splints is through the
roof: the number of kids with broken bones is massive, and they will need
as many as they can get.

🌐 [Hogar Bambi website](https://hogarbambi.org/)

🖨️ This means there is still a lot to print. Every part counts, and each
one you make can reach a child who needs it.

🤝 **Point of contact:** Pati. She is in direct contact with the charity
(and is being connected with a children's hospital to confirm exactly what
they need), and she will help make sure the printed parts reach the people
who need them.

🙏 If you can print, please join in. We will keep this request updated as
we learn more about the specific needs.

**Thank you for helping. We are counting on your solidarity!** 💚

---

## 🌎 Español

### 🦴 Se necesitan férulas para Hogar Bambi (niños en Venezuela)

La necesidad de férulas sigue siendo enorme. 💔

Nos pusimos en contacto con una de las organizadoras de **Hogar Bambi**,
una fundación para niños en Venezuela. Ella nos cuenta que la necesidad de
férulas está por las nubes: la cantidad de niños con huesos rotos es
enorme, y van a necesitar todas las que se puedan conseguir.

🌐 [Sitio web de Hogar Bambi](https://hogarbambi.org/)

🖨️ Esto significa que todavía hay mucho por imprimir. Cada pieza cuenta, y
cada una que hagas puede llegar a un niño que la necesita.

🤝 **Punto de contacto:** Pati. Ella está en contacto directo con la
fundación (y la están conectando con un hospital infantil para confirmar
exactamente qué necesitan), y ayudará a asegurar que las piezas impresas
lleguen a quienes las necesitan.

🙏 Si puedes imprimir, por favor súmate. Mantendremos esta solicitud
actualizada a medida que conozcamos más sobre las necesidades específicas.

**Gracias por ayudar. ¡Contamos con tu solidaridad!** 💚
```
```
