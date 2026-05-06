import { useEffect, useState, useRef } from 'react';

interface Heading {
  depth: number;
  slug: string;
  text: string;
}

interface TableOfContentsProps {
  headings: Heading[];
  currentPath?: string;
}

export default function TableOfContents({ headings, currentPath }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>('');
  const [collapsed, setCollapsed] = useState(false);
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    if (headings.length === 0) return;

    const headingElements = headings
      .map(h => document.getElementById(h.slug))
      .filter(Boolean) as HTMLElement[];

    observerRef.current = new IntersectionObserver(
      (entries) => {
        // Find the topmost visible heading
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => {
            const aTop = a.boundingClientRect.top;
            const bTop = b.boundingClientRect.top;
            return aTop - bTop;
          });

        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      {
        rootMargin: '-80px 0px -70% 0px',
        threshold: 0,
      }
    );

    headingElements.forEach(el => observerRef.current?.observe(el));

    // Set initial active
    if (headingElements[0]) {
      setActiveId(headingElements[0].id);
    }

    return () => observerRef.current?.disconnect();
  }, [currentPath]);

  if (headings.length === 0) return null;

  return (
    <nav
      id="toc"
      className="sticky top-24 text-sm max-h-[calc(100vh-8rem)] overflow-y-auto scrollbar-thin pr-1"
      aria-label="Table of contents"
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between w-full text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors cursor-pointer bg-transparent border-none mb-2 pr-1"
      >
        <span>目录</span>
        <svg
          className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 ${collapsed ? '-rotate-90' : 'rotate-0'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        className={`transition-all duration-200 ${collapsed ? 'max-h-0 opacity-0' : 'max-h-[calc(100vh-8rem)] opacity-100'}`}
      >
        <ul className="space-y-1.5 border-l border-[var(--color-border)]">
          {headings.map((heading) => (
            <li key={heading.slug} style={{ paddingLeft: heading.depth === 3 ? '12px' : '0' }}>
              <a
                href={`#${heading.slug}`}
                className={`block py-1 transition-all duration-150 no-underline leading-snug ${
                  activeId === heading.slug
                    ? 'text-[var(--color-primary)] font-medium border-l-2 border-[var(--color-primary)] -ml-px pl-3'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] border-l-2 border-transparent -ml-px pl-3'
                }`}
              >
                {heading.text}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
