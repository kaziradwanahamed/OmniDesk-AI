"use client";

import * as React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";

function nodeText(node: React.ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeText).join("");
  if (React.isValidElement(node)) {
    return nodeText((node.props as { children?: React.ReactNode }).children);
  }
  return "";
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <button
      type="button"
      aria-label="Copy code"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard unavailable */
        }
      }}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-tertiary transition-colors hover:text-primary"
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

const components: Components = {
  p: ({ children }) => <p className="my-2.5 leading-relaxed">{children}</p>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-accent underline underline-offset-2 hover:opacity-80"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className="my-2.5 ml-5 list-disc space-y-1 marker:text-tertiary">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2.5 ml-5 list-decimal space-y-1 marker:text-tertiary">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => (
    <h1 className="mt-5 mb-2 text-lg font-semibold text-primary">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mt-5 mb-2 text-base font-semibold text-primary">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-4 mb-1.5 text-sm font-semibold text-primary">{children}</h3>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-2 border-strong pl-3 text-secondary italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-subtle" />,
  strong: ({ children }) => (
    <strong className="font-semibold text-primary">{children}</strong>
  ),
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-subtle">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-elevated">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b border-subtle px-3 py-2 text-left font-semibold text-primary">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-subtle px-3 py-2 align-top text-secondary">
      {children}
    </td>
  ),
  pre: ({ children }) => {
    const child = React.Children.toArray(children).find(
      React.isValidElement,
    ) as React.ReactElement<{ className?: string; children?: React.ReactNode }> | undefined;
    const className = child?.props?.className ?? "";
    const lang = /language-(\w+)/.exec(className)?.[1] ?? "text";
    const raw = nodeText(child?.props?.children);
    return (
      <div className="my-3 overflow-hidden rounded-lg border border-subtle bg-canvas">
        <div className="flex items-center justify-between border-b border-subtle bg-elevated px-3 py-1.5">
          <span className="font-mono text-[11px] uppercase tracking-wider text-tertiary">
            {lang}
          </span>
          <CopyButton text={raw} />
        </div>
        <pre className="overflow-x-auto p-3 text-[13px] leading-relaxed">
          {children}
        </pre>
      </div>
    );
  },
  code: ({ className, children }) => {
    const isBlock = /language-/.test(className ?? "");
    if (isBlock) {
      return <code className={className}>{children}</code>;
    }
    return (
      <code className="rounded border border-subtle bg-elevated px-1.5 py-0.5 font-mono text-[0.85em] text-primary">
        {children}
      </code>
    );
  },
};

export function Markdown({ content }: { content: string }) {
  return (
    <div className="text-[15px] text-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
