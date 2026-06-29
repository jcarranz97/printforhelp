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
    <div className="prose-comment flex flex-col gap-2 text-sm leading-relaxed [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-default-300 [&_blockquote]:pl-3 [&_blockquote]:text-muted [&_code]:rounded [&_code]:bg-default-100 [&_code]:px-1 [&_em]:italic [&_h1]:text-lg [&_h1]:font-bold [&_h2]:text-base [&_h2]:font-bold [&_h3]:font-semibold [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
          img: ({ alt, ...props }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              {...props}
              alt={alt ?? ""}
              loading="lazy"
              className="my-1 h-auto max-w-full rounded-md border border-default-200"
            />
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
