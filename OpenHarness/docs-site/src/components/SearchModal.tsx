import { useEffect, useState, useRef, useCallback } from 'react';
import Fuse from 'fuse.js';

interface SearchResult {
  id: string;
  title: string;
  description: string;
  section: string;
  href: string;
  content?: string;
}

interface SearchIndex {
  docs: SearchResult[];
}

const SECTION_LABELS: Record<string, string> = {
  overview: '总览',
  architecture: '架构',
  workflows: '工作流',
  modules: '模块',
  reference: '参考',
  appendix: '附录',
  user: '用户手册',
};

const SECTION_COLORS: Record<string, string> = {
  overview: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  architecture: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  workflows: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  modules: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  reference: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  appendix: 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-300',
  user: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
};

export default function SearchModal() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState(0);
  const [fuse, setFuse] = useState<Fuse<SearchResult> | null>(null);
  const [index, setIndex] = useState<SearchIndex | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Load search index
  useEffect(() => {
    fetch('/search-index.json')
      .then(r => r.json())
      .then((data: SearchIndex) => {
        setIndex(data);
        const f = new Fuse(data.docs, {
          keys: [
            { name: 'title', weight: 0.4 },
            { name: 'description', weight: 0.3 },
            { name: 'content', weight: 0.2 },
            { name: 'section', weight: 0.1 },
          ],
          threshold: 0.3,
          includeScore: true,
          minMatchCharLength: 2,
        });
        setFuse(f);
      })
      .catch(() => {
        console.error('Failed to load search index');
      });
  }, []);

  // Listen for open-search event
  useEffect(() => {
    function handleOpen() { setOpen(true); }
    window.addEventListener('open-search', handleOpen);
    return () => window.removeEventListener('open-search', handleOpen);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      setQuery('');
      setResults([]);
      setSelected(0);
    }
  }, [open]);

  // Search
  useEffect(() => {
    if (!fuse || !query.trim()) {
      setResults([]);
      setSelected(0);
      return;
    }
    const r = fuse.search(query).slice(0, 8);
    setResults(r.map(x => x.item));
    setSelected(0);
  }, [query, fuse]);

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.children[selected] as HTMLElement;
    el?.scrollIntoView({ block: 'nearest' });
  }, [selected]);

  const close = useCallback(() => {
    setOpen(false);
    window.dispatchEvent(new CustomEvent('close-search'));
  }, []);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    e.stopPropagation();
    if (e.key === 'Escape') {
      close();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected(s => Math.min(s + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected(s => Math.max(s - 1, 0));
    } else if (e.key === 'Enter' && results[selected]) {
      window.location.href = results[selected].href;
    }
  }, [results, selected, close]);

  // Stop arrow key propagation so they don't trigger prev/next doc navigation
  const handleContainerKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (['ArrowDown', 'ArrowUp', 'Escape'].includes(e.key)) {
      e.stopPropagation();
    }
  }, []);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[10vh] px-4"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div
        className="relative w-full max-w-2xl bg-[var(--color-bg)] rounded-xl shadow-2xl border border-[var(--color-border)] overflow-hidden animate-fade-in"
        onKeyDown={handleContainerKeyDown}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)]">
          <svg className="w-5 h-5 text-[var(--color-text-muted)] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            autoFocus
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索文档..."
            className="flex-1 bg-transparent text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] outline-none text-base"
          />
          <kbd className="text-xs px-2 py-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded text-[var(--color-text-muted)] font-mono">Esc</kbd>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto">
          {query && results.length === 0 && (
            <div className="py-12 text-center text-[var(--color-text-muted)]">
              <div className="text-4xl mb-3">🔍</div>
              <p className="text-sm">未找到「{query}」相关文档</p>
            </div>
          )}

          {!query && index && (
            <div className="py-6 px-4">
              <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                全部文档 ({index.docs.length})
              </div>
              <ul>
                {index.docs.slice(0, 6).map((doc, i) => (
                  <ResultItem key={doc.id} doc={doc} isSelected={i === selected} onClick={() => { window.location.href = doc.href; }} />
                ))}
              </ul>
            </div>
          )}

          {query && results.length > 0 && (
            <ul ref={listRef}>
              {results.map((doc, i) => (
                <ResultItem key={doc.id} doc={doc} isSelected={i === selected} onClick={() => { window.location.href = doc.href; }} />
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-[var(--color-border)] bg-[var(--color-surface)] text-xs text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-[var(--color-bg)] border border-[var(--color-border)] rounded font-mono">↑↓</kbd>
            导航
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-[var(--color-bg)] border border-[var(--color-border)] rounded font-mono">↵</kbd>
            打开
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-[var(--color-bg)] border border-[var(--color-border)] rounded font-mono">Esc</kbd>
            关闭
          </span>
        </div>
      </div>
    </div>
  );
}

function ResultItem({ doc, isSelected, onClick }: { doc: SearchResult; isSelected: boolean; onClick: () => void }) {
  const section = doc.id.split('/')[0] || 'overview';
  const colorClass = SECTION_COLORS[section] || 'bg-gray-100 text-gray-700';

  return (
    <li>
      <button
        onClick={onClick}
        className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors ${
          isSelected ? 'bg-[var(--color-primary)]/10' : 'hover:bg-[var(--color-surface)]'
        }`}
      >
        <span className={`mt-0.5 px-2 py-0.5 text-2xs font-medium rounded ${colorClass}`}>
          {SECTION_LABELS[section] || section}
        </span>
        <div className="min-w-0 flex-1">
          <div className={`text-sm font-medium truncate ${isSelected ? 'text-[var(--color-primary)]' : 'text-[var(--color-text)]'}`}>
            {doc.title}
          </div>
          {doc.description && (
            <div className="text-xs text-[var(--color-text-muted)] mt-0.5 truncate">
              {doc.description}
            </div>
          )}
        </div>
        {isSelected && (
          <svg className="w-4 h-4 text-[var(--color-primary)] flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
          </svg>
        )}
      </button>
    </li>
  );
}
