import { visit } from 'unist-util-visit';

export function remarkMermaid() {
  let conversionCount = 0;

  return (tree) => {
    console.log('[rehype-mermaid] Plugin called, tree type:', tree.type);
    visit(tree, (node, index, parent) => {
      if (node.type !== 'element') return;
      if (node.tagName !== 'pre') return;

      // Check data-language on pre element (set by Shiki)
      const dataLang = node.properties?.dataLanguage;
      if (dataLang !== 'mermaid') return;

      // Find code element inside pre
      const codeNode = node.children?.find(child =>
        child.type === 'element' && child.tagName === 'code'
      );
      if (!codeNode) return;

      // Extract text content
      const textContent = extractText(codeNode);
      if (!textContent.trim()) return;

      // Create mermaid-block element
      const mermaidElement = {
        type: 'element',
        tagName: 'mermaid-block',
        properties: { 'data-definition': textContent },
        children: [],
      };

      if (parent && typeof index === 'number') {
        parent.children.splice(index, 1, mermaidElement);
        conversionCount++;
      }
    });

    if (conversionCount > 0) {
      console.log(`[rehype-mermaid] Converted ${conversionCount} mermaid code blocks`);
    }
  };
}

function extractText(node) {
  if (!node) return '';
  if (node.type === 'text') return node.value || '';
  if (node.children && Array.isArray(node.children)) {
    return node.children.map(extractText).join('');
  }
  return '';
}
