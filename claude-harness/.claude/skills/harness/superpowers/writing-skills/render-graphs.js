#!/usr/bin/env node
/**
 * Render graphviz diagrams from a skill's SKILL.md to SVG files.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function extractDotBlocks(markdown) {
  const blocks = [];
  const regex = /```dot\n([\s\S]*?)```/g;
  let match;
  while ((match = regex.exec(markdown)) !== null) {
    const content = match[1].trim();
    const nameMatch = content.match(/digraph\s+(\w+)/);
    const name = nameMatch ? nameMatch[1] : `graph_${blocks.length + 1}`;
    blocks.push({ name, content });
  }
  return blocks;
}

function renderToSvg(dotContent) {
  try {
    return execSync('dot -Tsvg', { input: dotContent, encoding: 'utf-8' });
  } catch (err) {
    console.error('Error running dot:', err.message);
    return null;
  }
}

function main() {
  const args = process.argv.slice(2);
  const skillDir = path.resolve(args[0]);
  const skillFile = path.join(skillDir, 'SKILL.md');
  
  if (!fs.existsSync(skillFile)) {
    console.error(`Error: ${skillFile} not found`);
    process.exit(1);
  }

  const markdown = fs.readFileSync(skillFile, 'utf-8');
  const blocks = extractDotBlocks(markdown);
  
  console.log(`Found ${blocks.length} diagram(s)`);
  
  const outputDir = path.join(skillDir, 'diagrams');
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);
  
  for (const block of blocks) {
    const svg = renderToSvg(block.content);
    if (svg) {
      fs.writeFileSync(path.join(outputDir, `${block.name}.svg`), svg);
      console.log(`Rendered: ${block.name}.svg`);
    }
  }
}

main();
