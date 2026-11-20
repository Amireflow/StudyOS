import { Fragment, useState, type ReactNode } from 'react';
import { Copy01Icon, Tick01Icon } from '@hugeicons/core-free-icons';
import { cn } from '../../lib/cn';
import { Icon } from './Icon';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

const SAFE_HTTP_URL = /^https?:\/\/[^\s)]+$/i;

function renderInline(text: string): ReactNode[] {
  const tokens: ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const codeMatch = remaining.match(/`([^`]+)`/);
    const linkMatch = remaining.match(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/i);
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
    const italicMatch = remaining.match(/(?<!\*)\*([^*\n]+)\*(?!\*)/);

    const candidates = [
      codeMatch ? { kind: 'code' as const, match: codeMatch } : null,
      linkMatch ? { kind: 'link' as const, match: linkMatch } : null,
      boldMatch ? { kind: 'bold' as const, match: boldMatch } : null,
      italicMatch ? { kind: 'italic' as const, match: italicMatch } : null,
    ]
      .filter(
        (item): item is { kind: 'code' | 'link' | 'bold' | 'italic'; match: RegExpMatchArray } =>
          item !== null && item.match.index !== undefined,
      )
      .sort((a, b) => (a.match.index ?? 0) - (b.match.index ?? 0));

    if (candidates.length === 0) {
      tokens.push(remaining);
      break;
    }

    const chosen = candidates[0];
    const start = chosen.match.index ?? 0;

    if (start > 0) {
      tokens.push(remaining.slice(0, start));
    }

    const full = chosen.match[0];
    if (chosen.kind === 'code') {
      tokens.push(
        <code
          key={`md-code-${key++}`}
          className="rounded-md bg-zinc-200/80 px-1.5 py-0.5 font-mono text-[0.85em] text-zinc-900 dark:bg-zinc-700/80 dark:text-zinc-100"
        >
          {chosen.match[1]}
        </code>,
      );
    } else if (chosen.kind === 'link') {
      const label = chosen.match[1];
      const href = chosen.match[2];
      if (SAFE_HTTP_URL.test(href)) {
        tokens.push(
          <a
            key={`md-link-${key++}`}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-teal-700 underline decoration-teal-500/50 underline-offset-2 transition-colors hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300"
          >
            {label}
          </a>,
        );
      } else {
        tokens.push(label);
      }
    } else if (chosen.kind === 'bold') {
      tokens.push(
        <strong key={`md-bold-${key++}`} className="font-semibold text-zinc-950 dark:text-zinc-50">
          {renderInline(chosen.match[1])}
        </strong>,
      );
    } else {
      tokens.push(
        <em key={`md-em-${key++}`} className="italic">
          {renderInline(chosen.match[1])}
        </em>,
      );
    }

    remaining = remaining.slice(start + full.length);
  }

  return tokens;
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(code);
      }
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-xl bg-zinc-900 text-zinc-100 dark:bg-zinc-950">
      <div className="flex items-center justify-between bg-zinc-800/90 px-3.5 py-2 text-[11px] font-medium text-zinc-300 dark:bg-zinc-900">
        <span className="font-mono uppercase tracking-wider text-teal-300">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={() => void handleCopy()}
          aria-label="Copier le code"
          className="inline-flex items-center gap-1 rounded-md bg-zinc-700/70 px-2 py-1 text-[11px] font-medium text-zinc-100 transition-colors hover:bg-zinc-600/80"
        >
          <Icon icon={copied ? Tick01Icon : Copy01Icon} size={13} />
          <span>{copied ? 'Copié' : 'Copier'}</span>
        </button>
      </div>
      <pre className="overflow-x-auto p-3.5 font-mono text-xs leading-relaxed text-zinc-100">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function isTableSeparatorLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.includes('|')) return false;
  const cells = trimmed
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim());
  return cells.length > 0 && cells.every((c) => /^:?-{2,}:?$/.test(c));
}

function splitTableCells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim());
}

function getCalloutClasses(text: string): string {
  const trimmed = text.trim();
  if (/^(attention|pi[èe]ge|important|erreur)\b/i.test(trimmed)) {
    return 'rounded-xl bg-amber-50/80 px-3.5 py-2.5 text-sm leading-relaxed text-amber-950 dark:bg-amber-950/40 dark:text-amber-100';
  }
  if (/^(astuce|conseil|[àa]\s+retenir|bon\s+[àa]\s+savoir|note)\b/i.test(trimmed)) {
    return 'rounded-xl bg-teal-50/75 px-3.5 py-2.5 text-sm leading-relaxed text-teal-950 dark:bg-teal-950/40 dark:text-teal-100';
  }
  return 'rounded-xl bg-zinc-100/85 px-3.5 py-2.5 text-sm leading-relaxed text-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-300';
}

function isSpecialLineStart(line: string): boolean {
  const trimmed = line.trim();
  return (
    trimmed.startsWith('```') ||
    trimmed.startsWith('>') ||
    /^#{1,4}\s+/.test(trimmed) ||
    /^(-|\*)\s+/.test(trimmed) ||
    /^\d+\.\s+/.test(trimmed) ||
    /^([-*_])\1{2,}$/.test(trimmed)
  );
}

/**
 * Rendu Markdown sécurisé (sans HTML brut), adapté aux explications de cours,
 * tableaux, blocs de code copiables, callouts pédagogiques et liens http(s).
 */
export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: ReactNode[] = [];
  let idx = 0;

  while (idx < lines.length) {
    const rawLine = lines[idx];
    const line = rawLine.trim();

    if (!line) {
      idx += 1;
      continue;
    }

    // Fenced code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      idx += 1;
      const codeLines: string[] = [];
      while (idx < lines.length && !lines[idx].trim().startsWith('```')) {
        codeLines.push(lines[idx]);
        idx += 1;
      }
      if (idx < lines.length && lines[idx].trim().startsWith('```')) {
        idx += 1;
      }
      blocks.push(<CodeBlock key={`blk-${idx}`} language={lang} code={codeLines.join('\n')} />);
      continue;
    }

    // Horizontal rule
    if (/^([-*_])\1{2,}$/.test(line)) {
      blocks.push(<div key={`hr-${idx}`} className="my-3 h-px bg-zinc-200/80 dark:bg-zinc-800" />);
      idx += 1;
      continue;
    }

    // Markdown table
    if (
      line.includes('|') &&
      idx + 1 < lines.length &&
      isTableSeparatorLine(lines[idx + 1])
    ) {
      const headers = splitTableCells(line);
      idx += 2;
      const bodyRows: string[][] = [];
      while (idx < lines.length && lines[idx].trim().includes('|') && lines[idx].trim() !== '') {
        bodyRows.push(splitTableCells(lines[idx]));
        idx += 1;
      }
      blocks.push(
        <div
          key={`tbl-${idx}`}
          className="my-3 overflow-x-auto rounded-xl bg-zinc-50 dark:bg-zinc-800/60"
        >
          <table className="w-full text-left text-xs leading-relaxed">
            <thead className="bg-zinc-100/90 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100">
              <tr>
                {headers.map((head, hIdx) => (
                  <th key={`th-${hIdx}`} className="px-3 py-2 font-semibold">
                    {renderInline(head)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-zinc-700 dark:text-zinc-300">
              {bodyRows.map((row, rIdx) => (
                <tr
                  key={`tr-${rIdx}`}
                  className="odd:bg-transparent even:bg-white/70 dark:even:bg-zinc-900/40"
                >
                  {headers.map((_, cIdx) => (
                    <td key={`td-${rIdx}-${cIdx}`} className="px-3 py-2 align-top">
                      {renderInline(row[cIdx] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Headings
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = renderInline(headingMatch[2]);
      if (level === 1) {
        blocks.push(
          <h2
            key={`h-${idx}`}
            className="mt-4 first:mt-0 text-base font-bold tracking-tight text-zinc-950 dark:text-zinc-50"
          >
            {headingText}
          </h2>,
        );
      } else if (level === 2) {
        blocks.push(
          <h3
            key={`h-${idx}`}
            className="mt-4 first:mt-0 text-sm font-bold tracking-tight text-zinc-900 dark:text-zinc-100"
          >
            {headingText}
          </h3>,
        );
      } else {
        blocks.push(
          <h4
            key={`h-${idx}`}
            className="mt-3 first:mt-0 text-[13px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-100"
          >
            {headingText}
          </h4>,
        );
      }
      idx += 1;
      continue;
    }

    // Blockquotes / callouts
    if (line.startsWith('>')) {
      const quoteLines: string[] = [];
      while (idx < lines.length && lines[idx].trim().startsWith('>')) {
        quoteLines.push(lines[idx].trim().replace(/^>\s?/, ''));
        idx += 1;
      }
      const joined = quoteLines.join(' ');
      blocks.push(
        <div key={`quote-${idx}`} className={cn('my-2.5', getCalloutClasses(joined))}>
          {renderInline(joined)}
        </div>,
      );
      continue;
    }

    // Unordered list
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const items: string[] = [];
      while (
        idx < lines.length &&
        (lines[idx].trim().startsWith('- ') || lines[idx].trim().startsWith('* '))
      ) {
        items.push(lines[idx].trim().slice(2));
        idx += 1;
      }
      blocks.push(
        <ul key={`ul-${idx}`} className="my-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
          {items.map((item, i) => (
            <li key={`li-${i}`}>{renderInline(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list
    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (idx < lines.length && /^\d+\.\s+/.test(lines[idx].trim())) {
        items.push(lines[idx].trim().replace(/^\d+\.\s+/, ''));
        idx += 1;
      }
      blocks.push(
        <ol key={`ol-${idx}`} className="my-2 list-decimal space-y-1.5 pl-5 text-sm leading-relaxed">
          {items.map((item, i) => (
            <li key={`oli-${i}`}>{renderInline(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // Paragraph (join contiguous plain lines)
    const paraLines: string[] = [line];
    idx += 1;
    while (
      idx < lines.length &&
      lines[idx].trim() !== '' &&
      !isSpecialLineStart(lines[idx]) &&
      !(
        lines[idx].includes('|') &&
        idx + 1 < lines.length &&
        isTableSeparatorLine(lines[idx + 1])
      )
    ) {
      paraLines.push(lines[idx].trim());
      idx += 1;
    }
    blocks.push(
      <p key={`p-${idx}`} className="my-2 text-sm leading-relaxed first:mt-0 last:mb-0">
        {paraLines.map((pl, pIdx) => (
          <Fragment key={`pl-${pIdx}`}>
            {pIdx > 0 && ' '}
            {renderInline(pl)}
          </Fragment>
        ))}
      </p>,
    );
  }

  return (
    <div className={cn('space-y-1.5 text-zinc-800 dark:text-zinc-200', className)}>
      {blocks}
    </div>
  );
}
