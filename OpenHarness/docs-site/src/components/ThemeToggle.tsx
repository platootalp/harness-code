import { useEffect, useState, useRef } from 'react';
import type { ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'system';

const labels: Record<Theme, string> = {
  light: '浅色',
  dark: '深色',
  system: '跟随系统',
};

const icons: Record<Theme, ReactNode> = {
  light: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  ),
  dark: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  ),
  system: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  ),
};

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>('system');
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem('theme') as Theme | null;
    const initial = stored || 'system';
    setTheme(initial);
    applyTheme(initial);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function applyTheme(t: Theme) {
    const root = document.documentElement;
    root.classList.remove('dark');
    if (t === 'dark') {
      root.classList.add('dark');
    }
  }

  function select(t: Theme) {
    setTheme(t);
    setOpen(false);
    localStorage.setItem('theme', t);
    applyTheme(t);
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          setOpen(!open);
        }}
        className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-600 dark:text-gray-300"
        aria-label="切换主题"
        aria-expanded={open}
      >
        {icons[theme]}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-36 bg-white dark:bg-[#1a1f35] border border-[var(--color-border)] rounded-lg shadow-lg py-1 z-50">
          {(Object.keys(labels) as Theme[]).map((t) => (
            <button
              key={t}
              onClick={() => select(t)}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition ${
                theme === t ? 'text-[var(--color-primary)] font-medium' : 'text-[var(--color-text)]'
              }`}
            >
              <span className="w-4 h-4 flex items-center justify-center">{icons[t]}</span>
              {labels[t]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
