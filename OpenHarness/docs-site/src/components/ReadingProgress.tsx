import { useEffect, useState } from 'react';

export default function ReadingProgress() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    function updateProgress() {
      const doc = document.getElementById('doc-content');
      if (!doc) return;

      const rect = doc.getBoundingClientRect();
      const totalHeight = doc.scrollHeight;
      const viewportHeight = window.innerHeight;
      const scrolled = window.scrollY - (doc.offsetTop - 64); // subtract nav height
      const available = totalHeight - viewportHeight + 64;

      const pct = Math.min(100, Math.max(0, (scrolled / available) * 100));
      setProgress(pct);
    }

    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();

    return () => window.removeEventListener('scroll', updateProgress);
  }, []);

  return (
    <div
      className="reading-progress"
      style={{ width: `${progress}%` }}
      role="progressbar"
      aria-valuenow={Math.round(progress)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Reading progress"
    />
  );
}
