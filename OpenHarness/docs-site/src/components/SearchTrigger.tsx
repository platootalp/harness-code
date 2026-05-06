import { useEffect, useState } from 'react';

export default function SearchTrigger() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function handleOpen() { setIsOpen(true); }
    function handleClose() { setIsOpen(false); }
    window.addEventListener('open-search', handleOpen);
    window.addEventListener('close-search', handleClose);
    return () => {
      window.removeEventListener('open-search', handleOpen);
      window.removeEventListener('close-search', handleClose);
    };
  }, []);

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 's' || e.key === '/') {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('open-search'));
      }
    }
    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
  }, []);

  return (
    <button
      onClick={() => window.dispatchEvent(new CustomEvent('open-search'))}
      aria-label="打开搜索"
      aria-expanded={isOpen}
      className="flex items-center gap-2 px-3 py-1.5 text-sm text-[var(--color-text-muted)] bg-[var(--color-surface)] hover:bg-[var(--color-border)] border border-[var(--color-border)] rounded-md transition-all group"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <span className="hidden sm:inline text-xs">搜索...</span>
      <kbd className="hidden sm:inline text-2xs px-1.5 py-0.5 bg-[var(--color-bg)] border border-[var(--color-border)] rounded text-[10px] font-mono group-hover:border-[var(--color-text-muted)]">
        ⌘K
      </kbd>
    </button>
  );
}
