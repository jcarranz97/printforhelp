/** Locale → dictionary lookup. */

import type { Locale } from "../config";

import { type Dictionary, es } from "./es";
import { en } from "./en";

const DICTIONARIES: Record<Locale, Dictionary> = { es, en };

/** Return the message catalog for a locale. */
export function getDictionary(locale: Locale): Dictionary {
  return DICTIONARIES[locale];
}

export type { Dictionary };
