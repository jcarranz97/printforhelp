/** Country helpers for the directory badges.
 *
 * Collection centers store the country as a free-text human name (e.g.
 * "Venezuela", "Canadá", "UK"), so the flag is derived by mapping known names
 * to an ISO 3166-1 alpha-2 code; a value that is already a bare 2-letter code
 * is accepted as-is. Unknown values get no flag (the UI falls back to 🌍).
 */

const CODE_RE = /^[A-Z]{2}$/;

/** Known country-name spellings (EN + ES, accent variants) → ISO alpha-2. */
const NAME_TO_CODE: Record<string, string> = {
  argentina: "AR",
  bolivia: "BO",
  colombia: "CO",
  germany: "DE",
  alemania: "DE",
  mexico: "MX",
  méxico: "MX",
  portugal: "PT",
  uk: "GB",
  "united kingdom": "GB",
  "reino unido": "GB",
  "great britain": "GB",
  usa: "US",
  "united states": "US",
  "estados unidos": "US",
  venezuela: "VE",
  canada: "CA",
  canadá: "CA",
  panama: "PA",
  panamá: "PA",
};

/** Resolve a stored country value (name or code) to an ISO alpha-2, or null. */
function toCode(value: string): string | null {
  const trimmed = value.trim();
  const named = NAME_TO_CODE[trimmed.toLowerCase()];
  if (named) {
    return named;
  }
  const cc = trimmed.toUpperCase();
  return CODE_RE.test(cc) ? cc : null;
}

/** Emoji flag for a country name or ISO code, or null when unrecognized. */
export function countryFlag(value: string): string | null {
  const code = toCode(value);
  if (!code) {
    return null;
  }
  // Regional-indicator symbols: "A" (0x1F1E6) + the letter's offset.
  const base = 0x1f1e6;
  return String.fromCodePoint(
    base + (code.charCodeAt(0) - 65),
    base + (code.charCodeAt(1) - 65),
  );
}

/** Display name for a stored country value.
 *
 * A human name is shown as-is; a bare 2-letter code is expanded to its
 * localized region name (falling back to the raw value).
 */
export function countryName(value: string, locale: string): string {
  const trimmed = value.trim();
  const cc = trimmed.toUpperCase();
  // Only expand a bare code — stored names are already human-readable.
  if (CODE_RE.test(cc) && !(trimmed.toLowerCase() in NAME_TO_CODE)) {
    try {
      const name = new Intl.DisplayNames([locale], { type: "region" }).of(cc);
      if (name && name !== cc) {
        return name;
      }
    } catch {
      // Intl.DisplayNames unsupported for this runtime/locale — use the value.
    }
  }
  return value;
}
