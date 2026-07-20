"use client";

import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { profileHref } from "@/lib/profile-href";

/** Minimal hast node shape we touch in the mention plugin. */
type HastNode = {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
};

// Matches an @username token. The capture starts with an alphanumeric so
// trailing punctuation is excluded; the leading group keeps ordinary emails
// in prose from matching. The optional `@domain` tail (and `+` in the local
// part) is for legacy handles that are themselves email addresses — see
// MENTION_PATTERN in the backend, which this mirrors exactly.
const MENTION_RE =
  /(^|[^\w@])@([A-Za-z0-9][A-Za-z0-9_.+-]*(?:@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)?)/g;

// Never rewrite mentions inside these elements (links, code, images).
const SKIP_TAGS = new Set(["a", "code", "pre"]);

function splitTextNode(
  value: string,
  targets: Record<string, string>,
): HastNode[] {
  const out: HastNode[] = [];
  let last = 0;
  MENTION_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MENTION_RE.exec(value)) !== null) {
    const [, lead, token] = match;
    // Longest first: `@someone@gmail.com` is a legacy email handle if one
    // exists, otherwise it is `someone` with an address written after them.
    const written = token.includes("@")
      ? [token, token.split("@")[0]].find(
          (candidate) => targets[candidate.toLowerCase()] !== undefined,
        )
      : token;
    // The name as it stands today: a mention written before a rename must
    // read as who that person is now, not as a handle nobody answers to.
    const name = written && targets[written.toLowerCase()];
    if (!written || !name) {
      continue;
    }
    const atIndex = match.index + lead.length;
    if (atIndex > last) {
      out.push({ type: "text", value: value.slice(last, atIndex) });
    }
    // A link, not a span: a mention names a real user, so it should reach
    // their profile. A handle with no profile page (a system account whose
    // name is a route) stays highlighted but unlinked.
    const href = profileHref(name);
    out.push({
      type: "element",
      tagName: href ? "a" : "span",
      properties: href
        ? { className: ["mention"], href }
        : { className: ["mention"] },
      children: [{ type: "text", value: `@${name}` }],
    });
    last = atIndex + 1 + written.length;
  }
  if (out.length === 0) {
    return [{ type: "text", value }];
  }
  if (last < value.length) {
    out.push({ type: "text", value: value.slice(last) });
  }
  return out;
}

/** Concatenate every bit of text under a node. */
function textOf(node: HastNode): string {
  if (node.type === "text") {
    return node.value ?? "";
  }
  return (node.children ?? []).map(textOf).join("");
}

/**
 * Undo GFM's email autolinking when the address is really a tagged user.
 *
 * `@someone@host.com` is one token to the writer, but GFM sees an email in
 * the tail and links it — so tagging a legacy account whose handle is an
 * address turned into a one-click `mailto:` that published that address to
 * every reader. An `<a href="mailto:">` sitting directly after a text node
 * ending in `@` is never an address the author meant to publish; it is a
 * mention the parser tore in half, so it is folded back into plain text.
 */
function unwrapTaggedEmails(children: HastNode[]): HastNode[] {
  const out: HastNode[] = [];
  for (const child of children) {
    const href = child.properties?.href;
    const previous = out[out.length - 1];
    const isMailto =
      child.type === "element" &&
      child.tagName === "a" &&
      typeof href === "string" &&
      href.startsWith("mailto:");
    if (
      isMailto &&
      previous?.type === "text" &&
      previous.value?.endsWith("@")
    ) {
      previous.value += textOf(child);
      continue;
    }
    out.push(child);
  }
  return out;
}

/** rehype plugin: turn valid @mentions into links to their profile. */
function rehypeMentions(targets: Record<string, string>) {
  return () => (tree: HastNode) => {
    const walk = (node: HastNode, parentTag?: string) => {
      if (!node.children) {
        return;
      }
      const skip = parentTag !== undefined && SKIP_TAGS.has(parentTag);
      const next: HastNode[] = [];
      // Repair torn-apart mentions first, so the pass below sees the whole
      // token as one text node.
      for (const child of unwrapTaggedEmails(node.children)) {
        if (child.type === "text" && !skip && child.value) {
          next.push(...splitTextNode(child.value, targets));
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
 * - `mentions` maps each valid @mention to the current username it refers
 *   to, and each becomes a link to that profile. A mention written before
 *   the person renamed is displayed under their new name.
 */
export function Markdown({
  source,
  mentions,
}: {
  source: string;
  mentions?: Record<string, string>;
}) {
  // Always applied, even with nothing to link: the pass also repairs
  // mentions GFM mangled into `mailto:` links, and a comment that tags only
  // an email-shaped handle resolves to no mentions at all — exactly the case
  // that needs repairing.
  const rehypePlugins = [rehypeMentions(mentions ?? {})] as RehypePlugins;

  return (
    <div className="prose-comment flex flex-col gap-2 text-sm leading-relaxed [&_.mention]:font-medium [&_.mention]:text-[color:var(--accent-strong)] [&_.mention:hover]:underline [&_a:not(.mention)]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-default-300 [&_blockquote]:pl-3 [&_blockquote]:text-muted [&_code]:rounded [&_code]:bg-default-100 [&_code]:px-1 [&_em]:italic [&_h1]:text-lg [&_h1]:font-bold [&_h2]:text-base [&_h2]:font-bold [&_h3]:font-semibold [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={rehypePlugins}
        components={{
          a: (props) =>
            // Mentions stay in this tab — they point at our own profile
            // pages, and a new tab per @name would be hostile. Everything
            // else is an outside link and keeps the reader on the page.
            props.className?.split(" ").includes("mention") ? (
              <a {...props} />
            ) : (
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
