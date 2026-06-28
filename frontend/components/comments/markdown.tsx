"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Minimal Markdown renderer for comment bodies (FR-131).
 *
 * - GFM extensions enabled (tables, strikethrough, autolinks).
 * - Raw HTML is intentionally NOT rendered (no rehype-raw) so comment
 *   bodies cannot inject scripts or markup.
 * - Links open in a new tab so the reader keeps the center page.
 */
export function Markdown({ source }: { source: string }) {
  return (
    <div className="prose-comment flex flex-col gap-2 text-sm leading-relaxed [&_a]:underline [&_code]:rounded [&_code]:bg-default-100 [&_code]:px-1 [&_li]:ml-4 [&_li]:list-disc [&_strong]:font-semibold">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
