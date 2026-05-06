// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import { remarkMermaid } from './src/lib/remark-mermaid.mjs';
import { rehypeCallout } from './src/lib/rehype-callout.ts';

// https://astro.build/config
export default defineConfig({
  integrations: [
    react(),
    tailwind(),
  ],
  output: 'static',
  markdown: {
    remarkPlugins: [],
    rehypePlugins: [remarkMermaid, rehypeCallout],
    shikiConfig: {
      themes: {
        light: 'github-light',
        dark: 'github-dark',
      },
    },
  },
  vite: {
    optimizeDeps: {
      include: ['mermaid', 'react', 'react-dom', 'react-dom/client'],
    },
  },
});
