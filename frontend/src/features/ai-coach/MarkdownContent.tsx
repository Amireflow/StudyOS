import { Fragment, ReactNode } from 'react';
import { cn } from '../../lib/cn';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

const INLINE_TOKEN_RE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g;

function renderInline(text: string): ReactNode[] {
  const parts = text.split(INLINE_TOKEN_RE);
  return parts.filter(Boolean).map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={idx} className="font-semibold text-zinc-900 dark:text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={idx}
          className="rounded bg-zinc-200/70 px-1.5 py-0.5 font-mono text-[0.8em] text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return (
        <em key={idx} className="italic text-zinc-800 dark:text-zinc-200">
          {part.slice(1, -1)}
        </em>
      );
    }
    return <Fragment key={idx}>{part}</Fragment>;
  });
}

interface ListItem {
  text: string;
  children: string[];
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    // Headings (#, ##, ###)
    const headingMatch = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      blocks.push(
        <h3
          key={`h-${i}`}
          className={cn(
            'font-semibold tracking-tight text-zinc-900 dark:text-zinc-100',
            level <= 2 ? 'mt-3 text-sm first:mt-0' : 'mt-2.5 text-[13px] first:mt-0',
          )}
        >
          {renderInline(headingText)}
        </h3>,
      );
      i += 1;
      continue;
    }

    // Blockquote lines (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i += 1;
      }
      blocks.push(
        <blockquote
          key={`q-${i}`}
          className="rounded-xl bg-amber-50/90 px-3 py-2 text-xs leading-relaxed text-amber-900 dark:bg-amber-950/35 dark:text-amber-200"
        >
          {quoteLines.map((line, lineIdx) => (
            <p key={lineIdx} className={lineIdx > 0 ? 'mt-1' : undefined}>
              {renderInline(line)}
            </p>
          ))}
        </blockquote>,
      );
      continue;
    }

    // Unordered list (- ... with nested indented - ...)
    if (/^[-*]\s+/.test(trimmed)) {
      const items: ListItem[] = [];
      while (i < lines.length) {
        const line = lines[i];
        const lineTrimmed = line.trim();
        if (!lineTrimmed) break;

        const nestedMatch = /^\s{2,}[-*]\s+(.+)$/.exec(line);
        if (nestedMatch && items.length > 0) {
          items[items.length - 1].children.push(nestedMatch[1]);
          i += 1;
          continue;
        }

        const topMatch = /^[-*]\s+(.+)$/.exec(lineTrimmed);
        if (topMatch) {
          items.push({ text: topMatch[1], children: [] });
          i += 1;
          continue;
        }

        break;
      }

      blocks.push(
        <ul key={`ul-${i}`} className="space-y-1.5 pl-1">
          {items.map((item, itemIdx) => (
            <li key={itemIdx} className="text-[13.5px] leading-relaxed text-zinc-700 dark:text-zinc-300">
              <div className="flex items-start gap-2">
                <span
                  aria-hidden="true"
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600/80 dark:bg-teal-400/80"
                />
                <span className="min-w-0 flex-1">{renderInline(item.text)}</span>
              </div>
              {item.children.length > 0 && (
                <ul className="mt-1 space-y-1 pl-4">
                  {item.children.map((child, childIdx) => (
                    <li
                      key={childIdx}
                      className="flex items-start gap-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400"
                    >
                      <span
                        aria-hidden="true"
                        className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-zinc-400 dark:bg-zinc-500"
                      />
                      <span className="min-w-0 flex-1">{renderInline(child)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list (1. ...)
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length) {
        const lineTrimmed = lines[i].trim();
        const ordMatch = /^\d+\.\s+(.+)$/.exec(lineTrimmed);
        if (!ordMatch) break;
        items.push(ordMatch[1]);
        i += 1;
      }

      blocks.push(
        <ol key={`ol-${i}`} className="space-y-1.5 pl-1">
          {items.map((itemText, itemIdx) => (
            <li
              key={itemIdx}
              className="flex items-start gap-2 text-[13.5px] leading-relaxed text-zinc-700 dark:text-zinc-300"
            >
              <span className="mt-0.5 shrink-0 font-mono text-xs font-medium text-teal-700 dark:text-teal-400">
                {itemIdx + 1}.
              </span>
              <span className="min-w-0 flex-1">{renderInline(itemText)}</span>
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    // Paragraph (collect contiguous plain lines)
    const paraLines: string[] = [];
    while (i < lines.length) {
      const candidate = lines[i].trim();
      if (
        !candidate ||
        /^(#{1,3})\s+/.test(candidate) ||
        candidate.startsWith('>') ||
        /^[-*]\s+/.test(candidate) ||
        /^\d+\.\s+/.test(candidate)
      ) {
        break;
      }
      paraLines.push(candidate);
      i += 1;
    }

    blocks.push(
      <p key={`p-${i}`} className="text-[13.5px] leading-relaxed text-zinc-700 dark:text-zinc-300">
        {paraLines.map((line, lineIdx) => (
          <Fragment key={lineIdx}>
            {lineIdx > 0 && ' '}
            {renderInline(line)}
          </Fragment>
        ))}
      </p>,
    );
  }

  return <div className={cn('space-y-2', className)}>{blocks}</div>;
}
