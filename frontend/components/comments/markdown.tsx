"use client";

import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Minimal hast node shape we touch in the mention plugin. */
type HastNode = {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
};

// Matches an @username token. The capture starts with an alphanumeric so
// trailing punctuation is excluded; the leading group keeps emails from
// matching (mirrors the backend MENTION_PATTERN).
const MENTION_RE = /(^|[^\w@])@([A-Za-z0-9][A-Za-z0-9_.-]*)/g;

// Never rewrite mentions inside these elements (links, code, images).
const SKIP_TAGS = new Set(["a", "code", "pre"]);

function splitTextNode(value: string, valid: Set<string>): HastNode[] {
  const out: HastNode[] = [];
  let last = 0;
  MENTION_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MENTION_RE.exec(value)) !== null) {
    const [, lead, name] = match;
    if (!valid.has(name.toLowerCase())) {
      continue;
    }
    const atIndex = match.index + lead.length;
    if (atIndex > last) {
      out.push({ type: "text", value: value.slice(last, atIndex) });
    }
    out.push({
      type: "element",
      tagName: "span",
      properties: { className: ["mention"] },
      children: [{ type: "text", value: `@${name}` }],
    });
    last = atIndex + 1 + name.length;
  }
  if (out.length === 0) {
    return [{ type: "text", value }];
  }
  if (last < value.length) {
    out.push({ type: "text", value: value.slice(last) });
  }
  return out;
}

/** rehype plugin: wrap valid @mentions in a styled span. */
function rehypeMentions(valid: Set<string>) {
  return () => (tree: HastNode) => {
    const walk = (node: HastNode, parentTag?: string) => {
      if (!node.children) {
        return;
      }
      const skip = parentTag !== undefined && SKIP_TAGS.has(parentTag);
      const next: HastNode[] = [];
      for (const child of node.children) {
        if (child.type === "text" && !skip && child.value) {
          next.push(...splitTextNode(child.value, valid));
        } else {
          if (child.type === "element") {
            walk(child, child.tagName);
          }
          next.push(child);
        }
      }
      node.children = next;
    };
    walk(tree);
  };
}

type RehypePlugins = ComponentProps<typeof ReactMarkdown>["rehypePlugins"];

/**
 * Minimal Markdown renderer for comment bodies (FR-131).
 *
 * - GFM extensions enabled (tables, strikethrough, autolinks).
 * - Raw HTML is intentionally NOT rendered (no rehype-raw) so comment
 *   bodies cannot inject scripts or markup.
 * - Links open in a new tab so the reader keeps the center page.
 * - `mentions` (valid usernames) are highlighted so it's clear the tag
 *   landed on a real user.
 */
export function Markdown({
  source,
  mentions,
}: {
  source: string;
  mentions?: string[];
}) {
  const valid = new Set((mentions ?? []).map((m) => m.toLowerCase()));
  const rehypePlugins = (
    valid.size ? [rehypeMentions(valid)] : []
  ) as RehypePlugins;

  return (
    <div className="prose-comment flex flex-col gap-2 text-sm leading-relaxed [&_.mention]:font-medium [&_.mention]:text-[color:var(--accent-strong)] [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-default-300 [&_blockquote]:pl-3 [&_blockquote]:text-muted [&_code]:rounded [&_code]:bg-default-100 [&_code]:px-1 [&_em]:italic [&_h1]:text-lg [&_h1]:font-bold [&_h2]:text-base [&_h2]:font-bold [&_h3]:font-semibold [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={rehypePlugins}
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
