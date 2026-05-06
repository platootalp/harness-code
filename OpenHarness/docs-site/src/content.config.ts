import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DOCS_ROOT = resolve(__dirname, '../../docs');

const docs = defineCollection({
  loader: glob({
    pattern: '**/*.md',
    base: DOCS_ROOT,
  }),
  schema: z.object({
    title: z.string().optional(),
    description: z.string().optional(),
    lastUpdated: z.string().optional(),       // e.g. "2026-04-14"
    author: z.string().optional(),
    tags: z.array(z.string()).optional(),
    level: z.enum(['L1', 'L2', 'L3']).optional(),  // 文档深度级别
    related: z.array(z.string()).optional(),   // 相关文档 slug 列表
  }),
});

export const collections = { docs };
