/**
 * Build search index from docs/ markdown files
 * Run: node scripts/build-search-index.mjs
 */

import { readdir, readFile } from 'fs/promises';
import { join, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
// Project docs are in the parent repo root, not inside docs-site
const DOCS_ROOT = resolve(__dirname, '../../docs');
const OUTPUT = resolve(__dirname, '../public/search-index.json');

const SECTION_LABELS = {
  overview: '总览',
  architecture: '架构',
  workflows: '工作流',
  modules: '模块',
  reference: '参考',
  appendix: '附录',
  user: '用户手册',
};

async function extractFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return {};
  const fm = {};
  for (const line of match[1].split('\n')) {
    const [key, ...rest] = line.split(':');
    if (key && rest.length) {
      fm[key.trim()] = rest.join(':').trim().replace(/^["']|["']$/g, '');
    }
  }
  return fm;
}

async function extractHeadings(content) {
  const headings = [];
  const regex = /^#{1,3}\s+(.+)$/gm;
  let match;
  while ((match = regex.exec(content)) !== null) {
    headings.push(match[1].replace(/[*_`]/g, ''));
  }
  return headings.join(' ');
}

async function buildIndex() {
  const docs = [];

  async function walk(dir) {
    const entries = await readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
      } else if (entry.name.endsWith('.md')) {
        const relative = full.replace(DOCS_ROOT + '/', '');
        const content = await readFile(full, 'utf-8');
        const fm = await extractFrontmatter(content);
        const headings = await extractHeadings(content);
        const slug = relative.replace(/\.md$/, '');

        const section = slug.split('/')[0] || 'overview';

        // Extract first paragraph as description
        const body = content
          .replace(/^---[\s\S]*?---\n/, '')
          .replace(/^#{1,6}\s+.+\n/gm, '')
          .replace(/```[\s\S]*?```/g, '')
          .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
          .replace(/[*_`~]/g, '')
          .trim();
        const firstPara = body.split('\n\n').find(p => p.trim().length > 30) || '';

        docs.push({
          id: slug,
          title: fm.title || slug.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
          description: fm.description || firstPara.slice(0, 120),
          section: SECTION_LABELS[section] || section,
          href: slug === 'index' ? '/docs/' : `/docs/${slug}/`,
          content: headings + ' ' + fm.description,
          lastUpdated: fm.lastUpdated || '',
        });
      }
    }
  }

  await walk(DOCS_ROOT);

  // Sort by href
  docs.sort((a, b) => a.href.localeCompare(b.href));

  const output = JSON.stringify({ docs }, null, 2);

  const { writeFile } = await import('fs/promises');
  await writeFile(OUTPUT, output, 'utf-8');

  console.log(`✓ Search index built: ${docs.length} docs -> public/search-index.json`);
}

buildIndex().catch(console.error);
