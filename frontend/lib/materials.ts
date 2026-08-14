/**
 * Print-material suggestions for the Part forms.
 *
 * Materials are free text on the API (like tags), so this list is a starting
 * point, never a whitelist — a creator can type anything, and whatever the
 * catalog already uses is offered alongside these.
 */
export const COMMON_MATERIALS = ["PLA", "PETG", "ABS", "ASA", "TPU", "PLA+"];

/**
 * Merge the materials already used across the catalog with the common ones,
 * de-duplicated case-insensitively. Catalog values come first and win the
 * casing, so a community that writes "petg" keeps seeing "petg".
 */
export function materialSuggestions(fromCatalog: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const material of [...fromCatalog, ...COMMON_MATERIALS]) {
    const value = material.trim();
    const key = value.toLowerCase();
    if (value && !seen.has(key)) {
      seen.add(key);
      result.push(value);
    }
  }
  return result;
}
