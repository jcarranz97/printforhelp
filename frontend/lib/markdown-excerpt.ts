/**
 * Strip Markdown to a clean, single-line plain-text excerpt for card
 * previews — so a long Markdown description (with headings, links, images,
 * etc.) doesn't dump raw syntax like "## 🌍 English ###" onto a card.
 */
export function markdownToExcerpt(source: string, maxChars = 200): string {
  const text = source
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ") // images -> drop
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1") // links -> link text
    .replace(/`{1,3}([^`]*)`{1,3}/g, "$1") // inline code / fences
    .replace(/^\s{0,3}#{1,6}\s+/gm, "") // headings
    .replace(/^\s{0,3}>\s?/gm, "") // blockquotes
    .replace(/^\s{0,3}[-*+]\s+/gm, "") // bullet lists
    .replace(/^\s{0,3}\d+\.\s+/gm, "") // ordered lists
    .replace(/[*_~]{1,3}/g, "") // emphasis / strikethrough markers
    .replace(/\s+/g, " ") // collapse whitespace + newlines
    .trim();
  if (text.length <= maxChars) {
    return text;
  }
  // Cut at the last word boundary within the limit.
  return `${text.slice(0, maxChars).replace(/\s+\S*$/, "")}…`;
}
